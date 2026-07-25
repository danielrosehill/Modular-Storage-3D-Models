"""Rewrite the model table in README.md from the upload ledger.

    python3 scripts/render_model_table.py

Replaces whatever sits between the MODEL-TABLE markers in README.md with a table
built from `specs/units.json` and `models/uploads.json`. The published links are
generated rather than pasted, so they cannot drift from what is actually live -
re-run this after any upload.

Thumbnails point at the local preview renders under `models/<CODE>/`, not at
Sketchfab's CDN: the CDN thumbnails are only produced once processing finishes
and their URLs are not stable, whereas the local renders are committed.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage_models import glb_stats

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
LEDGER = REPO / "models" / "uploads.json"

START = "<!-- MODEL-TABLE:START -->"
END = "<!-- MODEL-TABLE:END -->"

COLLECTION_URL = "https://sketchfab.com/danielrosehill/collections/industrial-storage"

FAMILY_LABEL = {
    "euro_stacking_container": "Euro stacking container",
    "attached_lid_container": "Attached-lid container",
    "open_front_picking_bin": "Open-front picking bin",
    "shelving": "Shelving bay",
}


def dims(unit):
    return " × ".join(str(v) for v in unit["outer_mm"].values())


def main():
    spec = json.loads((REPO / "specs" / "units.json").read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}

    rows = [
        "| | Unit | External (mm) | Tris | View |",
        "|---|---|---|---|---|",
    ]
    for unit in spec["units"]:
        code = unit["code"]
        entry = ledger.get(code)
        thumb = f"models/{code}/{code}.jpg"
        img = f'<img src="{thumb}" width="150">'
        if entry:
            img = f'<a href="{entry["url"]}">{img}</a>'
            view = f'[View in 3D]({entry["url"]})'
        else:
            view = "_not published_"

        glb = REPO / "models" / code / f"{code}.glb"
        tris = f"{glb_stats(glb)[0]:,}" if glb.exists() else "—"

        name = f'**{FAMILY_LABEL.get(unit["family"], unit["family"])}**<br>`{code}`'
        rows.append(f'| {img} | {name} | {dims(unit)} | {tris} | {view} |')

    table = "\n".join(rows)
    block = (f"{START}\n\n{table}\n\n"
             f"All eight are collected at "
             f"[**Industrial Storage**]({COLLECTION_URL}) on Sketchfab, "
             f"CC BY 4.0.\n\n{END}")

    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"README.md is missing the {START} / {END} markers")

    head, rest = text.split(START, 1)
    _old, tail = rest.split(END, 1)
    README.write_text(head + block + tail, encoding="utf-8")

    published = sum(1 for u in spec["units"] if u["code"] in ledger)
    print(f"model table rewritten: {published}/{len(spec['units'])} published")


if __name__ == "__main__":
    main()
