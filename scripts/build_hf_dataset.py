"""Assemble the Hugging Face dataset tree from models/ and specs/units.json.

    python3 scripts/build_hf_dataset.py            # writes hf-dataset/
    hf upload danielrosehill/Modular-Storage-3D-Models hf-dataset . --repo-type dataset

Layout written to hf-dataset/ (gitignored, regenerable):

    README.md                     dataset card (from scripts/hf_card_header.md + a unit table)
    metadata.jsonl                one row per unit; `file_name` points at the preview
                                  image, so the HF dataset viewer shows a thumbnail
                                  grid (imagefolder convention) with the specs as columns
    units.json                    the full spec, unchanged
    models/<CODE>/<CODE>.glb      the asset
    models/<CODE>/<CODE>.jpg      preview render
    models/<CODE>/description.txt listing copy

The viewer cannot render GLB, so the preview JPG is the row's image and `glb` is
a plain path column. No third-party dependencies; JPGs are taken from models/
or converted from build/previews/*.png with ImageMagick if missing.
"""

import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "hf-dataset"
HF_ID = "danielrosehill/Modular-Storage-3D-Models"


def preview_jpg(unit, dest):
    code = unit["code"]
    staged = REPO / "models" / code / f"{code}.jpg"
    if staged.exists():
        shutil.copy2(staged, dest)
        return
    png = REPO / "build" / "previews" / f"{unit['id']}.png"
    if not png.exists():
        raise SystemExit(f"{code}: no preview (run render_previews.py)")
    subprocess.run(["convert", str(png), "-quality", "88", str(dest)], check=True)


def main():
    spec = json.loads((REPO / "specs" / "units.json").read_text(encoding="utf-8"))
    ledger = json.loads((REPO / "models" / "uploads.json").read_text(encoding="utf-8"))
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "models").mkdir(parents=True)

    rows = []
    for u in spec["units"]:
        code = u["code"]
        src = REPO / "models" / code
        dst = OUT / "models" / code
        dst.mkdir()
        shutil.copy2(src / f"{code}.glb", dst / f"{code}.glb")
        shutil.copy2(src / "description.txt", dst / "description.txt")
        preview_jpg(u, dst / f"{code}.jpg")
        rows.append({
            "file_name": f"models/{code}/{code}.jpg",
            "code": code,
            "name": u["name"],
            "family": u["family"],
            "region": u.get("region", "metric"),
            "outer_mm": u["outer_mm"],
            "outer_in": u.get("outer_in"),
            "cells": u.get("cells"),
            "open_deg": u.get("open_deg"),
            "reference_product": u.get("reference_product"),
            "glb": f"models/{code}/{code}.glb",
            "sketchfab_url": ledger.get(code, {}).get("url"),
            "dimension_confidence": u.get("dimension_confidence"),
        })

    with (OUT / "metadata.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    shutil.copy2(REPO / "specs" / "units.json", OUT / "units.json")

    def dims(r):
        d = r["outer_mm"]
        return " × ".join(str(v) for v in d.values()) + " mm (" + " × ".join(d) + ")"

    table = ["| Code | Unit | External | GLB |", "|---|---|---|---|"]
    for r in rows:
        table.append(f"| `{r['code']}` | {r['name']} | {dims(r)} | "
                     f"[glb](https://huggingface.co/datasets/{HF_ID}/resolve/main/{r['glb']}) |")
    header = (REPO / "scripts" / "hf_card_header.md").read_text(encoding="utf-8")
    (OUT / "README.md").write_text(header.rstrip() + "\n\n## Units\n\n"
                                   + "\n".join(table) + "\n", encoding="utf-8")
    print(f"{len(rows)} units -> {OUT.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
