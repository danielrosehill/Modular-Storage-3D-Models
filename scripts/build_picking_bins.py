"""Generate GLB models for the open-front picking bins.

Run headless:

    blender --background --python scripts/build_picking_bins.py -- --out build

All three bin sizes are the same moulding, so this is one parametric build driven
by the depth/width/height in specs/units.json. Axes: X is depth with the open
face at -X, Y is width, Z is height with the origin at the centre of the base.

Construction:

    A tapered body - B cavity - C front opening

The body tapers inward toward the base, which is what lets the bins stack into
one another - the same job the inset foot skirt does on the euroboxes, done by
draft angle instead of by a step. The front opening is a single rotated box
subtraction: the cut plane passes through the top of the front wall and rises to
full height partway back, which produces the front wall, the sloping side edges
and the full-height back wall in one operation.

Not modelled, and deliberately so per the fidelity target in the README: the
recessed grid panels on the side walls, the front label recess, the notched rear
flange and the side mounting hole. All are surface detail that costs geometry and
reads as noise at the sizes the website and WMS render these at.
"""

import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boxlib import (clear_scene, cuboid, tapered_box, boolean, bevel_and_smooth,
                    make_material, export_glb, print_summary, load_spec,
                    add_labels, wall_placements, fit_size)

# --- parameters, millimetres ------------------------------------------------
WALL = 3.0            # wall thickness; these mouldings are chunkier than a crate
BASE = 4.0            # floor slab thickness
TAPER = 0.90          # bottom face as a fraction of the top - the nesting draft
BEVEL = 2.0           # edge radius

FRONT_H_FRAC = 0.42   # front wall height as a fraction of the back wall
SLOPE_END_FRAC = 0.55 # how far back the side edge reaches full height

# Labels go on the back and both sides. The front is cut away, and what is left
# of it is too low to carry text.
LABEL_FACES = ("+x", "-y", "+y")
LABEL_PROUD = 0.4
LABEL_Z_FRAC = 0.30   # low enough to sit under the sloping side edge
LABEL_MAX_SIZE = 34.0
LABEL_RGB = (0.90, 0.92, 0.94)


def build_bin(name, depth, width, height):
    body = tapered_box(f"{name}_body", (depth, width, height),
                       (0, 0, height / 2), bottom_scale=TAPER)

    # interior cavity, open topped, floor sitting on the base slab
    cav_h = height
    cav = tapered_box(f"{name}_cav",
                      (depth - 2 * WALL, width - 2 * WALL, cav_h),
                      (0, 0, BASE + cav_h / 2), bottom_scale=TAPER)
    boolean(body, cav, "DIFFERENCE")

    # front opening: one plane cut through (front face, front wall top) rising to
    # full height at SLOPE_END_FRAC back. Behind that point the plane is above
    # the body, so the back wall is left intact.
    front_h = FRONT_H_FRAC * height
    run = SLOPE_END_FRAC * depth
    rise = height - front_h
    theta = math.atan2(rise, run)

    cut_h = 2 * height
    mid = (-depth / 2 + run / 2, 0.0, (front_h + height) / 2)
    perp = (-math.sin(theta), 0.0, math.cos(theta))
    centre = tuple(m + p * (cut_h / 2) for m, p in zip(mid, perp))

    cut = cuboid(f"{name}_front", (3 * depth, 3 * width, cut_h), centre,
                 rotation=(0.0, -theta, 0.0))
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
    # placeholder blue, same caveat as the euroboxes - see the README
    blue = (0.0, 0.319, 0.701)

    results = []
    for unit in spec["units"]:
        if unit["family"] != "open_front_picking_bin":
            continue
        clear_scene()
        d = unit["outer_mm"]
        obj = build_bin(unit["id"], d["depth"], d["width"], d["height"])
        obj.data.materials.append(make_material("picking_bin_blue", blue))

        label = unit.get("label")
        if label:
            h = d["height"]
            places = wall_placements(d["depth"], d["width"], h,
                                     h * LABEL_Z_FRAC, LABEL_PROUD,
                                     bottom_scale=TAPER, faces=LABEL_FACES)
            size = fit_size(label, min(p["face_w"] for p in places),
                            LABEL_MAX_SIZE)
            add_labels(obj, label, places,
                       make_material("label_white", LABEL_RGB, 0.5), size=size)
        results.append((unit["id"], *export_glb(obj, out_dir / f"{unit['id']}.glb")))

    print_summary(results)


if __name__ == "__main__":
    main()
