"""Assemble the publishable `models/` tree from the build output and the specs.

    python3 scripts/stage_models.py

`build/` is generator output and is keyed by unit id (`eurobox-600x400x230`).
`models/` is the distribution layout and is keyed by the short code (`EU6423`),
one self-contained folder per unit holding everything an upload needs:

    models/EU6423/EU6423.glb        the asset
    models/EU6423/EU6423.jpg        preview render, for the listing thumbnail
    models/EU6423/description.txt   human-readable listing copy
    models/EU6423/upload.json       the same copy, shaped for the Sketchfab API

Keeping this separate from `build/` means a rebuild never clobbers hand-edited
listing copy, and re-staging is safe to run at any time.

The listing copy is assembled rather than hand-written: editorial prose lives in
`specs/descriptions/<CODE>.md`, dimensions come from `specs/units.json`, and the
triangle/vertex/size figures are read out of the GLB itself. That last part is
the point - those numbers go stale the moment the geometry changes, and a
description claiming 2,900 triangles for a 30,000-triangle asset is worse than
no description at all.

No third-party dependencies and no Blender: this runs on a bare interpreter so
it can be re-run without the modelling toolchain present.
"""

import json
import re
import shutil
import struct
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUILD = REPO / "build"
PREVIEWS = BUILD / "previews"
PROSE = REPO / "specs" / "descriptions"
OUT = REPO / "models"

# Sketchfab licence slug, from GET /v3/licenses. `by` is CC Attribution 4.0 and
# matches the account's existing uploads.
LICENSE = "by"

# Sketchfab rejects the whole upload with HTTP 400 above these, so the API copy is
# generated separately from description.txt and the name is checked here rather
# than discovered halfway through a batch upload. Both verified 2026-07-25; neither
# limit is stated in the API docs.
SKETCHFAB_DESC_LIMIT = 1024
SKETCHFAB_NAME_LIMIT = 48

SECTION_RE = re.compile(r"^==\s*(\w+)\s*==\s*$", re.MULTILINE)

# glTF chunk type magic, little-endian, from the GLB container spec
CHUNK_JSON = 0x4E4F534A


def parse_prose(path: Path) -> dict:
    """Split a `== section ==` delimited prose file into a dict of blocks."""
    text = path.read_text(encoding="utf-8")
    parts = SECTION_RE.split(text)
    # split() gives [preamble, name, body, name, body, ...]
    return {parts[i].strip(): parts[i + 1].strip()
            for i in range(1, len(parts) - 1, 2)}


def glb_stats(path: Path) -> tuple:
    """Triangles, vertices and byte size, read straight out of the GLB.

    Parses only the JSON chunk - the accessor counts are all that is needed, so
    the binary payload never has to be walked.
    """
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise ValueError(f"{path} is not a GLB")
    total = struct.unpack("<I", data[8:12])[0]

    doc = None
    off = 12
    while off < total:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        if ctype == CHUNK_JSON:
            doc = json.loads(data[off + 8:off + 8 + clen].decode("utf-8"))
            break
        off += 8 + clen
    if doc is None:
        raise ValueError(f"{path} has no JSON chunk")

    accessors = doc.get("accessors", [])
    tris = verts = 0
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4:      # 4 == TRIANGLES, and the default
                continue
            attrs = prim.get("attributes", {})
            if "indices" in prim:
                tris += accessors[prim["indices"]]["count"] // 3
            elif "POSITION" in attrs:
                tris += accessors[attrs["POSITION"]]["count"] // 3
            if "POSITION" in attrs:
                verts += accessors[attrs["POSITION"]]["count"]
    return tris, verts, len(data)


def dimension_lines(outer_mm: dict) -> list:
    """One line per named dimension.

    Deliberately not collapsed into a single `L x W x H` string: the three
    families name their axes differently (length/width/height for the crates,
    depth/width/height for the bins, width/depth/height for the shelving) and
    flattening them into one ordered triple is exactly how a depth gets read as
    a length.
    """
    return [f"  {k.capitalize():<10s}{v} mm" for k, v in outer_mm.items()]


def build_description(unit, prose, stats) -> str:
    tris, verts, size = stats
    out = [unit["name"], unit["code"], ""]
    out += [prose["body"], ""]
    out += ["DIMENSIONS (external)"] + dimension_lines(unit["outer_mm"]) + [""]

    if unit.get("standard_context"):
        out += ["STANDARD", f"  {unit['standard_context']}", ""]

    out += ["TYPICAL USE", prose["use"], ""]
    out += [
        "ASSET NOTES",
        "  Format      GLB (glTF 2.0 binary), single file, no external textures",
        "  Scale       metres, real world - a 600 mm crate is 0.600 units long",
        "  Origin      centre of the base, +Z up",
        f"  Geometry    {tris:,} triangles, {verts:,} vertices",
        "  Materials   flat PBR base colours, no image maps",
        f"  File size   {size / 1024:.1f} KB",
        "",
        "LICENCE",
        "  CC Attribution 4.0 (CC BY 4.0)",
        "",
        "TAGS",
        f"  {prose['tags']}",
    ]
    return "\n".join(out) + "\n"


def first_paragraph(text: str) -> str:
    return text.split("\n\n", 1)[0].replace("\n", " ").strip()


def short_description(unit, prose, stats) -> str:
    """A condensed description for the Sketchfab API.

    Sketchfab hard-limits the `description` field to 1024 characters and rejects
    the whole upload with HTTP 400 if you exceed it, so the full description.txt
    cannot be posted as-is - it runs to roughly 2400. This keeps the opening
    paragraph, the dimensions and the facts a buyer actually filters on, and
    drops the extended use-case prose.
    """
    tris = stats[0]
    dims = ", ".join(f"{k} {v} mm" for k, v in unit["outer_mm"].items())
    parts = [first_paragraph(prose["body"]), f"External dimensions: {dims}."]
    if unit.get("standard_context"):
        parts.append(first_paragraph(unit["standard_context"]))
    parts.append(
        f"GLB (glTF 2.0), real-world scale in metres, origin at the centre of the "
        f"base. {tris:,} triangles, flat PBR base colours, no textures. CC BY 4.0."
    )

    out = "\n\n".join(parts)
    if len(out) > SKETCHFAB_DESC_LIMIT:
        out = out[:SKETCHFAB_DESC_LIMIT - 1].rsplit(" ", 1)[0] + "…"
    return out


def sketchfab_payload(unit, prose, stats) -> dict:
    if len(unit["name"]) > SKETCHFAB_NAME_LIMIT:
        raise ValueError(
            f'{unit["code"]}: name is {len(unit["name"])} chars, over the '
            f'Sketchfab limit of {SKETCHFAB_NAME_LIMIT}: {unit["name"]!r}')

    tags = [t.strip().lower().replace(" ", "-")
            for t in prose["tags"].replace("\n", " ").split(",") if t.strip()]
    return {
        "name": unit["name"],
        "description": short_description(unit, prose, stats),
        "tags": tags,
        "license": LICENSE,
        "summary": prose["summary"].replace("\n", " "),
    }


def main():
    spec = json.loads((REPO / "specs" / "units.json").read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)

    staged = []
    for unit in spec["units"]:
        code = unit["code"]
        glb = BUILD / f"{unit['id']}.glb"
        if not glb.exists():
            print(f"  SKIP {code}: {glb.relative_to(REPO)} not built")
            continue

        prose_path = PROSE / f"{code}.md"
        if not prose_path.exists():
            print(f"  SKIP {code}: no prose at {prose_path.relative_to(REPO)}")
            continue

        folder = OUT / code
        folder.mkdir(exist_ok=True)
        shutil.copy2(glb, folder / f"{code}.glb")

        preview = PREVIEWS / f"{unit['id']}.jpg"
        if preview.exists():
            shutil.copy2(preview, folder / f"{code}.jpg")

        prose = parse_prose(prose_path)
        stats = glb_stats(glb)
        description = build_description(unit, prose, stats)
        (folder / "description.txt").write_text(description, encoding="utf-8")
        (folder / "upload.json").write_text(
            json.dumps(sketchfab_payload(unit, prose, stats), indent=2) + "\n",
            encoding="utf-8")

        staged.append((code, unit["name"], *stats))

    print("\n=== staged ===")
    for code, name, tris, verts, size in staged:
        print(f"{code:9s} {name[:44]:46s} {tris:7,d} tris  {size/1024:7.1f} KB")
    print(f"\n{len(staged)} of {len(spec['units'])} units staged into models/")


if __name__ == "__main__":
    main()
