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


def summary_of(code):
    """First `== summary ==` block of specs/descriptions/<CODE>.md."""
    p = REPO / "specs" / "descriptions" / f"{code}.md"
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    if "== summary ==" not in text:
        return None
    block = text.split("== summary ==", 1)[1].split("==", 1)[0]
    return " ".join(block.split())


def glb_counts(path):
    import struct
    data = path.read_bytes()
    total = struct.unpack("<I", data[8:12])[0]
    off = 12
    while off < total:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        if ctype == 0x4E4F534A:
            doc = json.loads(data[off + 8:off + 8 + clen])
            break
        off += 8 + clen
    acc = doc.get("accessors", [])
    tris = verts = 0
    for m in doc.get("meshes", []):
        for prim in m.get("primitives", []):
            at = prim.get("attributes", {})
            if "POSITION" in at:
                verts += acc[at["POSITION"]]["count"]
            if "indices" in prim:
                tris += acc[prim["indices"]]["count"] // 3
    return tris, verts, len(data)


# Column order of metadata.jsonl - documented in scripts/hf_card_header.md.
def row_for(u, code, ledger, spec):
    glb = REPO / "models" / code / f"{code}.glb"
    tris, verts, size = glb_counts(glb)
    colour_hex = (spec["colours"].get(u.get("colour_ref", ""), {}) or {}).get("sampled_srgb_hex")
    return {
        "file_name": f"models/{code}/{code}.jpg",
        "id": u["id"],
        "code": code,
        "name": u["name"],
        "description": summary_of(code),
        "category": u["category"],
        "subcategory": u["subcategory"],
        "family": u["family"],
        "colour": u.get("colour"),
        "colour_hex": colour_hex[0] if colour_hex else None,
        "material": u.get("material"),
        "lid": u.get("lid"),
        "access": u.get("access"),
        "state": u.get("state"),
        "open_deg": u.get("open_deg"),
        "cells": u.get("cells"),
        "stackable": u.get("stackable"),
        "nestable": u.get("nestable"),
        "region": u["region"],
        "footprint_mm": u.get("footprint_mm"),
        "outer_mm": u["outer_mm"],
        "outer_in": u.get("outer_in"),
        "external_volume_l": u.get("external_volume_l"),
        "reference_product": u.get("reference_product"),
        "source": u.get("source"),
        "dimension_confidence": u.get("dimension_confidence"),
        "triangles": tris,
        "vertices": verts,
        "file_bytes": size,
        "glb": f"models/{code}/{code}.glb",
        "sketchfab_url": ledger.get(code, {}).get("url"),
        "license": "cc-by-4.0",
    }


def main():
    spec = json.loads((REPO / "specs" / "units.json").read_text(encoding="utf-8"))
    ledger = json.loads((REPO / "models" / "uploads.json").read_text(encoding="utf-8"))
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "models").mkdir(parents=True)

    ids = [u["id"] for u in spec["units"]]
    codes = [u["code"] for u in spec["units"]]
    if len(set(ids)) != len(ids) or len(set(codes)) != len(codes):
        raise SystemExit("duplicate id or code in specs/units.json")
    rows = []
    for u in spec["units"]:
        code = u["code"]
        src = REPO / "models" / code
        dst = OUT / "models" / code
        dst.mkdir()
        shutil.copy2(src / f"{code}.glb", dst / f"{code}.glb")
        shutil.copy2(src / "description.txt", dst / "description.txt")
        preview_jpg(u, dst / f"{code}.jpg")
        rows.append(row_for(u, code, ledger, spec))

    with (OUT / "metadata.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    shutil.copy2(REPO / "specs" / "units.json", OUT / "units.json")

    def dims(r):
        d = r["outer_mm"]
        return " × ".join(str(v) for v in d.values()) + " mm (" + " × ".join(d) + ")"

    table = ["| Code | Unit | Subcategory | External | GLB |", "|---|---|---|---|---|"]
    for r in rows:
        table.append(f"| `{r['code']}` | {r['name']} | {r['subcategory']} | {dims(r)} | "
                     f"[glb](https://huggingface.co/datasets/{HF_ID}/resolve/main/{r['glb']}) |")
    header = (REPO / "scripts" / "hf_card_header.md").read_text(encoding="utf-8")
    (OUT / "README.md").write_text(header.rstrip() + "\n\n## Units\n\n"
                                   + "\n".join(table) + "\n", encoding="utf-8")
    print(f"{len(rows)} units -> {OUT.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
