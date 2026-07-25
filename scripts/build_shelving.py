"""Generate a GLB model for the warehouse shelving bay.

Run headless:

    blender --background --python scripts/build_shelving.py -- --out build

Axes: X is width, Y is depth with the open face at -Y, Z is height with the
origin at the centre of the base footprint. That puts a bay at the same origin
convention as the boxes, so a bay and its contents can be instanced into a scene
without per-asset offsets.

Built from parts rather than booleans - four corner posts, a deck and a pair of
beams per level, and a diagonal brace on each side panel - then joined into one
mesh with a single material. No cutting is involved, so unlike the crates this
one has no boolean failure modes to check for.

The shelf pitch is the one number here with no source behind it: the supplier
lists the bay size but not the shelf count, so five levels is an assumption that
happens to give roughly 430 mm of clear height, which takes the tallest eurobox
(340 mm) with room to lift it out. Change LEVELS in the spec if the real unit
differs.
"""

import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boxlib import (clear_scene, cuboid, bevel_and_smooth, make_material,
                    export_glb, print_summary, load_spec, join_parts)

# --- parameters, millimetres ------------------------------------------------
POST = 45.0           # square corner post
DECK_T = 25.0         # shelf deck thickness
BEAM_H = 60.0         # front/back beam height
BEAM_D = 30.0         # front/back beam thickness
BRACE = 28.0          # diagonal brace section
BEVEL = 0.8

BOTTOM_DECK_Z = 120.0  # top surface of the lowest deck
TOP_MARGIN = 50.0      # gap between the top deck and the head of the posts


def build_shelving(name, width, depth, height, levels):
    parts = []

    # four corner posts, outer faces flush with the footprint
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cuboid(
                f"{name}_post{sx}{sy}", (POST, POST, height),
                (sx * (width - POST) / 2, sy * (depth - POST) / 2, height / 2)))

    span = width - 2 * POST          # clear width between the posts
    top_z = height - TOP_MARGIN
    step = (top_z - BOTTOM_DECK_Z) / (levels - 1) if levels > 1 else 0

    for i in range(levels):
        z = BOTTOM_DECK_Z + i * step
        parts.append(cuboid(f"{name}_deck{i}", (span, depth, DECK_T),
                            (0, 0, z - DECK_T / 2)))
        # beams sit under the deck, front and back
        for sy in (-1, 1):
            parts.append(cuboid(
                f"{name}_beam{i}{sy}", (span, BEAM_D, BEAM_H),
                (0, sy * (depth - BEAM_D) / 2, z - DECK_T - BEAM_H / 2)))

    # one diagonal brace per side panel, corner to corner in the YZ plane
    run, rise = depth - POST, top_z - BOTTOM_DECK_Z
    length = math.hypot(run, rise)
    angle = math.atan2(rise, run)
    for sx in (-1, 1):
        parts.append(cuboid(
            f"{name}_brace{sx}", (BRACE, length, BRACE),
            (sx * (width - POST) / 2, 0, (BOTTOM_DECK_Z + top_z) / 2),
            rotation=(angle, 0.0, 0.0)))

    body = join_parts(parts)
    bevel_and_smooth(body, BEVEL, segments=1)
    body.name = name
    body.data.name = name
    return body


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path("build")
    repo = Path(__file__).resolve().parent.parent
    out_dir = out if out.is_absolute() else repo / out
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = load_spec(repo)
    grey = tuple(spec["colours"]["steel_grey"]["gltf_base_color_factor_linear"])

    results = []
    for unit in spec["units"]:
        if unit["family"] != "shelving":
            continue
        clear_scene()
        d = unit["outer_mm"]
        obj = build_shelving(unit["id"], d["width"], d["depth"], d["height"],
                             unit.get("levels", 5))
        # a little metallic reads as painted steel under the neutral environment
        # both consumers use, without going fully mirror-like
        obj.data.materials.append(
            make_material("steel_grey", grey, roughness=0.5, metallic=0.35))
        results.append((unit["id"], *export_glb(obj, out_dir / f"{unit['id']}.glb")))

    print_summary(results)


if __name__ == "__main__":
    main()
