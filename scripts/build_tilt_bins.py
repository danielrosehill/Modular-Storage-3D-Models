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

import bpy
import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boxlib import (clear_scene, cuboid, boolean, bevel_and_smooth,
                    make_material, export_glb, print_summary, load_spec,
                    join_parts, MM)

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
BIN_WALL = 2.0        # acrylic bin wall
OPEN_TOP_DEG = 38.0   # open top meets the back arc this far back from vertical
ARC_STEPS = 8

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


def _prism(name, poly_xz, y0, y1):
    """Mesh prism: a 2D polygon in the XZ plane (mm) extruded from y0 to y1."""
    n = len(poly_xz)
    verts = [(x * MM, y0 * MM, z * MM) for x, z in poly_xz] + \
            [(x * MM, y1 * MM, z * MM) for x, z in poly_xz]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def bin_profile(depth_in, h, run):
    """Side profile of one bin in its own frame: pivot (bottom front edge) at the
    origin, +x into the housing, +z up. Returns (polygon, index of the opening edge).

    Shape: a sloped front face, a sloped open top, and a back wall that is an arc
    centred on the pivot. Every point inside the housing lies within radius h of
    the pivot, so the bin can swing open without hitting the housing top - the
    same constraint that makes real tilt bins wedge-shaped.
    """
    R = h - GAP
    reach = min(depth_in, R * 0.999)
    alpha = math.radians(OPEN_TOP_DEG)               # where the open top meets the arc
    alpha = min(alpha, math.asin(reach / R))
    poly = [(0.0, 0.0), (-run, h)]                   # pivot, front top
    a_end = math.asin(reach / R)                     # arc runs from alpha down to here,
    steps = ARC_STEPS                                # then straight down to the floor
    for i in range(steps + 1):
        a = alpha + (a_end - alpha) * i / steps
        poly.append((R * math.sin(a), R * math.cos(a)))
    if poly[-1][1] > 0.5:
        poly.append((reach, 0.0))
    return poly, 1                                   # edge 1 -> 2 is the open top


def build_bin(name, depth, cell_w, inner_h, y, open_deg):
    w = cell_w - 2 * GAP
    h = inner_h - 2 * GAP
    lean = math.radians(FRONT_LEAN_DEG)
    run = h * math.tan(lean)
    x_pivot = -depth / 2 - FRONT_PROUD + run         # bottom front edge
    z_pivot = SHELL + GAP
    depth_in = depth / 2 - BACK - GAP - x_pivot
    poly, open_edge = bin_profile(depth_in, h, run)

    # skin: one thin plate per profile edge except the open top, plus two sides
    parts = []
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cz = sum(p[1] for p in poly) / n
    for i in range(n):
        if i == open_edge:
            continue
        (x0, z0), (x1, z1) = poly[i], poly[(i + 1) % n]
        L = math.hypot(x1 - x0, z1 - z0) or 1.0
        nx, nz = -(z1 - z0) / L, (x1 - x0) / L       # a normal; flip it inward
        mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
        if (cx - mx) * nx + (cz - mz) * nz < 0:
            nx, nz = -nx, -nz
        quad = [(x0, z0), (x1, z1), (x1 + nx * BIN_WALL, z1 + nz * BIN_WALL),
                (x0 + nx * BIN_WALL, z0 + nz * BIN_WALL)]
        parts.append(_prism(f"{name}_e{i}", quad, -w / 2, w / 2))
    parts.append(_prism(f"{name}_sL", poly, -w / 2, -w / 2 + BIN_WALL))
    parts.append(_prism(f"{name}_sR", poly, w / 2 - BIN_WALL, w / 2))
    # finger lip along the front top edge
    lip = [(-run - LIP_OUT, h - LIP_H), (-run + 1, h - LIP_H), (-run + 1, h), (-run - LIP_OUT, h)]
    parts.append(_prism(f"{name}_lip", lip, -w / 2, w / 2))

    obj = join_parts(parts)
    # place: rotate about the pivot (top swings toward -X, the user), then move
    th = math.radians(open_deg)
    c, s_ = math.cos(th), math.sin(th)
    for v in obj.data.vertices:
        x, yy, z = v.co.x / MM, v.co.y / MM, v.co.z / MM
        xr, zr = x * c - z * s_, x * s_ + z * c
        v.co = ((xr + x_pivot) * MM, (yy + y) * MM, (zr + z_pivot) * MM)
    obj.data.update()
    return obj


def acrylic_material(rgb, alpha):
    mat = make_material("acrylic_clear", rgb, roughness=0.05)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Alpha"].default_value = alpha
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "BLEND"
        except (AttributeError, TypeError):
            pass
    return mat


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path("build")
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    repo = Path(__file__).resolve().parent.parent
    out_dir = out if out.is_absolute() else repo / out
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = load_spec(repo)
    acr = spec["colours"].get("tilt_acrylic", {})
    acr_rgb = tuple(acr.get("gltf_base_color_factor_linear", (0.82, 0.9, 0.95)))
    acr_alpha = acr.get("alpha", 0.28)

    results = []
    for unit in spec["units"]:
        if unit["family"] != "tilt_bin_unit" or (only and unit["code"] != only):
            continue
        clear_scene()
        d = unit["outer_mm"]
        depth, width, height = d["depth"], d["width"], d["height"]
        cells = unit["cells"]
        open_deg = unit.get("open_deg", 0.0)
        housing, cell_w = build_housing(unit["id"], depth, width, height, cells)
        bevel_and_smooth(housing, BEVEL)
        housing.data.materials.append(make_material("housing_grey", HOUSING_RGB))

        inner_w = width - 2 * SHELL
        bin_mat = acrylic_material(acr_rgb, acr_alpha)
        bins = []
        for i in range(cells):
            y = -inner_w / 2 + cell_w / 2 + i * (cell_w + DIVIDER)
            b = build_bin(f"{unit['id']}_bin{i}", depth, cell_w,
                          height - 2 * SHELL, y, open_deg)
            b.data.materials.clear()
            b.data.materials.append(bin_mat)
            bins.append(b)
        obj = join_parts([housing] + bins)
        obj.name = unit["id"]
        obj.data.name = unit["id"]
        results.append((unit["id"], *export_glb(obj, out_dir / f"{unit['id']}.glb")))

    print_summary(results)


if __name__ == "__main__":
    main()
