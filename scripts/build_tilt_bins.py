"""Generate GLB models for tilt-out bin units (Hebrew: "רב-תא", multi-cell).

Run headless:

    blender --background --python scripts/build_tilt_bins.py -- --out build

A tilt-out bin unit is a fixed open-front housing holding N bins side by side;
each bin pivots forward on its bottom edge to open. The ranges share one width
(600 mm in the metric range, 23 5/8 in in the inch catalogues) and vary the bin
count, so one parametric build covers the whole ladder: housing width/depth/height
and cell count come from specs/units.json.

Axes: X is depth with the open face at -X, Y is width, Z is height with the origin
at the centre of the base - the same convention as the picking bins.

Construction:

    A housing shell - B N bin fronts (closed position) - C label slot per bin

Bins are modelled closed. Each bin is a solid block filling its cell, because
behind a closed front the inside is never seen; its front face leans back by
FRONT_LEAN so the familiar sloped face reads, with a finger lip along the top and
a recessed label slot. Not modelled: the pivot pins, the stop tabs, and the
interlocking dovetails that join units side by side or stack them.
"""

import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boxlib import (clear_scene, cuboid, boolean, bevel_and_smooth,
                    make_material, export_glb, print_summary, load_spec,
                    join_parts)

# --- parameters, millimetres ------------------------------------------------
SHELL = 3.0           # housing side/top/bottom wall
BACK = 2.5            # housing back wall
DIVIDER = 1.5         # partition between cells
GAP = 1.2             # clearance around each bin inside its cell
FRONT_PROUD = 2.0     # bin front stands this far forward of the housing face
FRONT_LEAN_DEG = 8.0  # the bin front leans back from vertical
LIP_H = 4.0           # finger lip along the top of each bin front
LIP_OUT = 3.0
SLOT_W_FRAC = 0.62    # label slot width as a fraction of the bin width
SLOT_H_FRAC = 0.22    # label slot height as a fraction of the bin height
SLOT_DEPTH = 1.0
BEVEL = 1.2

HOUSING_RGB = (0.38, 0.40, 0.43)   # mid grey, typical housing moulding


def build_housing(name, depth, width, height, cells):
    shell = cuboid(f"{name}_housing", (depth, width, height), (0, 0, height / 2))
    inner_w = width - 2 * SHELL
    cav = cuboid(f"{name}_cav", (depth - BACK + 1, inner_w, height - 2 * SHELL),
                 (-BACK / 2 - 0.5, 0, height / 2))
    boolean(shell, cav, "DIFFERENCE")
    parts = [shell]
    cell_w = (inner_w - (cells - 1) * DIVIDER) / cells
    for i in range(1, cells):
        y = -inner_w / 2 + i * cell_w + (i - 0.5) * DIVIDER
        parts.append(cuboid(f"{name}_div{i}",
                            (depth - BACK, DIVIDER, height - 2 * SHELL),
                            (BACK / 2 * -1, y, height / 2)))
    return join_parts(parts), cell_w


def build_bin(name, depth, cell_w, inner_h, y):
    """One closed bin. Its front face slopes: the top edge sits FRONT_PROUD
    forward of the housing face and the bottom edge is set back by the lean,
    the shape of a bin already tipped a few degrees on its pivot."""
    w = cell_w - 2 * GAP
    h = inner_h - 2 * GAP
    z_bot = SHELL + GAP
    z_top = z_bot + h
    x_front = -depth / 2 - FRONT_PROUD          # top front edge
    x_back = depth / 2 - BACK - GAP
    body = cuboid(name, (x_back - x_front, w, h),
                  ((x_front + x_back) / 2, y, z_bot + h / 2))

    lean = math.radians(FRONT_LEAN_DEG)
    run = h * math.tan(lean)
    L = math.hypot(run, h)
    nx, nz = -h / L, -run / L                    # outward normal of the face
    big = 4 * max(h, depth)
    px, pz = x_front + run, z_bot                # bottom front edge
    cut = cuboid(f"{name}_lean", (big, 3 * w, 3 * big),
                 (px + nx * big / 2, y, pz + nz * big / 2),
                 rotation=(0.0, -lean, 0.0))
    boolean(body, cut, "DIFFERENCE")

    # recessed label slot on the upper part of the face
    sw, sh = SLOT_W_FRAC * w, SLOT_H_FRAC * h
    z_slot = z_bot + 0.72 * h
    x_face = x_front + run * (z_top - z_slot) / h
    slot = cuboid(f"{name}_slot", (2 * SLOT_DEPTH, sw, sh), (x_face, y, z_slot),
                  rotation=(0.0, -lean, 0.0))
    boolean(body, slot, "DIFFERENCE")

    # finger lip along the top edge, overhanging the face
    lip = cuboid(f"{name}_lip", (LIP_OUT + 4, w, LIP_H),
                 (x_front - LIP_OUT / 2 + 2, y, z_top - LIP_H / 2))
    return join_parts([body, lip])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path("build")
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    repo = Path(__file__).resolve().parent.parent
    out_dir = out if out.is_absolute() else repo / out
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = load_spec(repo)
    bin_rgb = tuple(spec["colours"]["picking_bin_blue"]["gltf_base_color_factor_linear"])

    results = []
    for unit in spec["units"]:
        if unit["family"] != "tilt_bin_unit" or (only and unit["code"] != only):
            continue
        clear_scene()
        d = unit["outer_mm"]
        depth, width, height = d["depth"], d["width"], d["height"]
        cells = unit["cells"]
        housing, cell_w = build_housing(unit["id"], depth, width, height, cells)
        bevel_and_smooth(housing, BEVEL)
        housing.data.materials.append(make_material("housing_grey", HOUSING_RGB))

        inner_w = width - 2 * SHELL
        bins = []
        for i in range(cells):
            y = -inner_w / 2 + cell_w / 2 + i * (cell_w + DIVIDER)
            b = build_bin(f"{unit['id']}_bin{i}", depth, cell_w,
                          height - 2 * SHELL, y)
            bevel_and_smooth(b, BEVEL * 0.6)
            bins.append(b)
        bin_mat = make_material("bin_blue", bin_rgb)
        for b in bins:
            b.data.materials.clear()
            b.data.materials.append(bin_mat)
        obj = join_parts([housing] + bins)
        obj.name = unit["id"]
        obj.data.name = unit["id"]
        results.append((unit["id"], *export_glb(obj, out_dir / f"{unit['id']}.glb")))

    print_summary(results)


if __name__ == "__main__":
    main()
