"""Generate GLB models for the straight-wall euro stacking containers.

Run headless:

    blender --background --python scripts/build_euroboxes.py -- --out build

Reads specs/units.json and emits one GLB per unit in the `euro_stacking_container`
family. Everything is modelled in metres, which is what glTF expects, so a 600 mm
crate is 0.6 units wide and drops into a scene at real-world scale with no
rescaling.

Construction, per the fidelity target in the README (correct outer dimensions,
wall thickness, rounded edges and a working stacking foot; no fine ribbing):

    (A body | B foot) - C cavity - D underside - E handle cutouts  + F labels

The foot skirt is inset slightly more than the wall is thick, so the foot of one
crate drops inside the rim of the crate below with a small clearance. That single
relationship is what makes the models stack correctly when instanced, so the
insets are derived from each other rather than being independent numbers.

Labels are raised text on all four walls, taken from the `label` field in the
spec. They are geometry rather than a texture: it keeps the asset a single
self-contained GLB with no image payload, and at the sizes both consumers render
these at, extruded text stays legible where a small texture would not.
"""

import bpy
import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boxlib import (clear_scene, cuboid, boolean, bevel_and_smooth,
                    make_material, export_glb, print_summary, load_spec,
                    add_labels, wall_placements)

# --- parameters, millimetres ------------------------------------------------
WALL = 2.5          # side wall thickness
BASE = 3.0          # floor slab thickness
FOOT_H = 15.0       # VDA 4500 stacking insertion depth
CLEARANCE = 0.5     # per-side slop so a foot drops into the rim below
BEVEL = 1.2         # edge radius
FOOT_INSET = WALL + CLEARANCE

# handle cutouts through the top rim of the long sides
HANDLE_W = 110.0
HANDLE_H = 38.0
HANDLE_BELOW_RIM = 26.0   # centre distance down from the rim

# raised labels
LABEL_PROUD = 0.3         # standoff from the wall face
LABEL_EXTRUDE = 0.7       # relief depth
LABEL_MAX_SIZE = 55.0     # cap so tall crates do not get absurd type
LABEL_Z_FRAC = 0.42       # up the wall; clears the handle cutouts near the rim
LABEL_CURVE_RES = 3       # font curve tessellation; see the note in boxlib.add_labels
LABEL_RGB = (0.82, 0.84, 0.86)


def build_crate(name, length, width, height, handles=True):
    """length/width/height are external, in mm. Origin at the centre of the base."""
    # A: main body, full footprint, from the top of the foot skirt upwards
    body_h = height - FOOT_H
    body = cuboid(f"{name}_body", (length, width, body_h),
                  (0, 0, FOOT_H + body_h / 2))

    # B: inset foot skirt, drops into the rim of the crate below
    foot = cuboid(f"{name}_foot",
                  (length - 2 * FOOT_INSET, width - 2 * FOOT_INSET, FOOT_H),
                  (0, 0, FOOT_H / 2))
    boolean(body, foot, "UNION")

    # C: interior cavity, open at the top, floor sitting on the foot skirt
    floor_top = FOOT_H + BASE
    cav_h = height - floor_top + 10          # overshoot to guarantee an open top
    cav = cuboid(f"{name}_cavity",
                 (length - 2 * WALL, width - 2 * WALL, cav_h),
                 (0, 0, floor_top + cav_h / 2))
    boolean(body, cav, "DIFFERENCE")

    # D: hollow underside, leaving a rim of wall thickness around the skirt
    und = cuboid(f"{name}_underside",
                 (length - 2 * (FOOT_INSET + WALL),
                  width - 2 * (FOOT_INSET + WALL), FOOT_H + 10),
                 (0, 0, FOOT_H / 2 - 5))
    boolean(body, und, "DIFFERENCE")

    # E: handle cutouts through the top rim on both long sides
    if handles and length >= 400 and height >= 140:
        cz = height - HANDLE_BELOW_RIM
        for sy in (-1, 1):
            cut = cuboid(f"{name}_handle{sy}",
                         (HANDLE_W, 2 * WALL + 4, HANDLE_H),
                         (0, sy * width / 2, cz))
            boolean(body, cut, "DIFFERENCE")

    bevel_and_smooth(body, BEVEL)
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
    # placeholder blue - see the colour section of the README, this is not a
    # verified reference and is deliberately one shared value for now
    blue = (0.008, 0.122, 0.738)

    results = []
    for unit in spec["units"]:
        if unit["family"] not in ("euro_stacking_container", "straight_wall_container"):
            continue
        clear_scene()
        d = unit["outer_mm"]
        obj = build_crate(unit["id"], d["length"], d["width"], d["height"])
        obj.data.materials.append(make_material("eurobox_blue", blue))

        label = unit.get("label")
        if label:
            h = d["height"]
            places = wall_placements(d["length"], d["width"], h,
                                     h * LABEL_Z_FRAC, LABEL_PROUD)
            add_labels(obj, label, places,
                       make_material("label_white", LABEL_RGB, 0.5),
                       size=min(h * 0.22, LABEL_MAX_SIZE),
                       extrude=LABEL_EXTRUDE, curve_res=LABEL_CURVE_RES)

        results.append((unit["id"], *export_glb(obj, out_dir / f"{unit['id']}.glb")))

    print_summary(results)


if __name__ == "__main__":
    main()
