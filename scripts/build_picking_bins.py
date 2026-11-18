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
import bpy
import bmesh
from boxlib import (clear_scene, cuboid, tapered_box, boolean, bevel_and_smooth,
                    make_material, export_glb, print_summary, load_spec,
                    add_labels, wall_placements, fit_size, join_parts, MM)

# --- parameters, millimetres ------------------------------------------------
WALL = 3.0            # wall thickness; these mouldings are chunkier than a crate
BASE = 4.0            # floor slab thickness
TAPER = 0.90          # bottom face as a fraction of the top - the nesting draft
BEVEL = 2.0           # edge radius

FRONT_H_FRAC = 0.42   # front wall height as a fraction of the back wall
SLOPE_END_FRAC = 0.55 # how far back the side edge reaches full height

# Labels go on the back and both sides. The front is cut away, and what is left
# of it is too low to carry text.
LABEL_FACES = ("+x",)   # back only: the side walls now carry ribs
LABEL_PROUD = 0.4
LABEL_Z_FRAC = 0.30   # low enough to sit under the sloping side edge
LABEL_MAX_SIZE = 34.0
LABEL_RGB = (0.90, 0.92, 0.94)


# --- moulding detail (added 2026-11-18 from a reference photo of the Israeli range):
# vertical ribs on the outside of the side and back walls with matching channels
# inside (the "notches"), a rim flange round the top edge, a recessed label panel
# and grip ledge on the front wall, and optionally the steel bar across the opening.
RIB_W = 7.0           # rib width
RIB_OUT = 2.5         # how far a rib stands proud of the wall
GROOVE = 1.6          # matching channel depth on the inside
RIB_PITCH = 95.0      # target spacing of side ribs along the full-height part
RIM_W = 4.0           # rim flange: outward overhang
RIM_H = 5.0           # rim flange: height
PANEL_W_FRAC = 0.62   # front label recess, as fractions of the front wall
PANEL_H_FRAC = 0.50
PANEL_DEPTH = 1.5
LEDGE_OUT = 5.0       # grip ledge under the label panel
LEDGE_H = 4.0
BAR_R = 2.5           # steel front bar radius
STEEL_RGB = (0.62, 0.64, 0.66)


def _box8(name, corners):
    """Hexahedron from 8 corners in mm: bottom 4 then top 4, same winding."""
    verts = [tuple(c * MM for c in v) for v in corners]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
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


def _scale(z, height):
    return TAPER + (1.0 - TAPER) * (z / height)


def _wall_top(x, depth, height):
    """Height of the side wall top at depth position x (front at -depth/2)."""
    front_h = FRONT_H_FRAC * height
    run = SLOPE_END_FRAC * depth
    t = (x + depth / 2) / run
    return height if t >= 1 else front_h + (height - front_h) * max(t, 0.0)


def _wall_strip(name, depth, width, height, axis, sign, pos, z0, z1, off_in, off_out):
    """A vertical strip lying on a tapered wall, following its draft.

    axis 'y': side wall at y = sign*half_width(z), strip centred on x = pos.
    axis 'x': back/front wall at x = sign*half_depth(z), strip centred on y = pos.
    off_in/off_out: extent across the wall surface (negative = into the wall).
    """
    c = []
    for z in (z0, z1):
        sc = _scale(z, height)
        if axis == "y":
            yw = sign * width / 2 * sc
            xs = (pos * sc - RIB_W / 2, pos * sc + RIB_W / 2)
            ring = [(xs[0], yw + sign * off_in), (xs[1], yw + sign * off_in),
                    (xs[1], yw + sign * off_out), (xs[0], yw + sign * off_out)]
            c += [(x, y, z) for x, y in ring]
        else:
            xw = sign * depth / 2 * sc
            ys = (pos * sc - RIB_W / 2, pos * sc + RIB_W / 2)
            ring = [(xw + sign * off_in, ys[0]), (xw + sign * off_in, ys[1]),
                    (xw + sign * off_out, ys[1]), (xw + sign * off_out, ys[0])]
            c += [(x, y, z) for x, y in ring]
    return _box8(name, c)


def add_detail(body, name, depth, width, height, front_bar):
    parts = [body]
    full_from = -depth / 2 + SLOPE_END_FRAC * depth
    span = depth / 2 - full_from - RIB_W
    n = max(2, round(span / RIB_PITCH) + 1)
    xs = [full_from + RIB_W + span * i / (n - 1) for i in range(n)]
    for sign in (-1, 1):
        for i, x in enumerate(xs):
            top = height - RIM_H
            parts.append(_wall_strip(f"{name}_rib{sign}{i}", depth, width, height,
                                     "y", sign, x, BASE, top, -0.4, RIB_OUT))
            boolean(body, _wall_strip(f"{name}_grv{sign}{i}", depth, width, height,
                                      "y", sign, x, BASE + 2, height + 1,
                                      -WALL - GROOVE, -WALL + 0.2), "DIFFERENCE")
    for j, yy in enumerate((-0.36 * width, 0.36 * width)):
        parts.append(_wall_strip(f"{name}_brib{j}", depth, width, height, "x", 1, yy,
                                 BASE, height - RIM_H, -0.4, RIB_OUT))
        boolean(body, _wall_strip(f"{name}_bgrv{j}", depth, width, height, "x", 1, yy,
                                  BASE + 2, height + 1, -WALL - GROOVE, -WALL + 0.2),
                "DIFFERENCE")

    # rim flange: back, the full-height part of each side, the slope, the front
    zt = height - RIM_H / 2
    parts.append(cuboid(f"{name}_rimB", (RIM_W + WALL, width + 2 * RIM_W, RIM_H),
                        (depth / 2 + (RIM_W - WALL) / 2, 0, zt)))
    for sign in (-1, 1):
        L = depth / 2 - full_from
        parts.append(cuboid(f"{name}_rimS{sign}", (L, RIM_W + WALL, RIM_H),
                            (full_from + L / 2, sign * (width / 2 + (RIM_W - WALL) / 2), zt)))
        x0, z0 = -depth / 2, FRONT_H_FRAC * height
        x1, z1 = full_from, height
        ang = math.atan2(z1 - z0, x1 - x0)
        Ls = math.hypot(x1 - x0, z1 - z0)
        parts.append(cuboid(f"{name}_rimSl{sign}", (Ls + RIM_H, RIM_W + WALL, RIM_H),
                            ((x0 + x1) / 2, sign * (width / 2 + (RIM_W - WALL) / 2),
                             (z0 + z1) / 2 - RIM_H / 2),
                            rotation=(0.0, -ang, 0.0)))
    fh = FRONT_H_FRAC * height
    parts.append(cuboid(f"{name}_rimF", (RIM_W + WALL, width + 2 * RIM_W, RIM_H),
                        (-depth / 2 - (RIM_W - WALL) / 2, 0, fh - RIM_H / 2)))

    # front label panel recess + grip ledge under it
    sc = _scale(fh * 0.5, height)
    pw, ph = PANEL_W_FRAC * width * sc, PANEL_H_FRAC * fh
    pz = fh * 0.58
    boolean(body, cuboid(f"{name}_panel", (2 * PANEL_DEPTH, pw, ph),
                         (-depth / 2 * _scale(pz, height), 0, pz)), "DIFFERENCE")
    lz = pz - ph / 2 - LEDGE_H / 2
    parts.append(cuboid(f"{name}_ledge", (LEDGE_OUT + 2, pw, LEDGE_H),
                        (-depth / 2 * _scale(lz, height) - LEDGE_OUT / 2 + 1, 0, lz)))

    joined = join_parts(parts)
    if front_bar:
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=BAR_R * MM,
                                            depth=(width + 2) * MM,
                                            location=((-depth / 2 + 6) * MM, 0,
                                                      (fh + BAR_R) * MM),
                                            rotation=(math.radians(90), 0, 0))
        bar = bpy.context.active_object
        bar.name = f"{name}_bar"
        bar.data.materials.append(make_material("steel", STEEL_RGB, 0.3, 0.9))
        return joined, bar
    return joined, None


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


ONLY = None


def main():
    global ONLY
    _a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ONLY = set(_a[_a.index("--only") + 1].split(",")) if "--only" in _a else None
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
        if unit["family"] != "open_front_picking_bin" or (ONLY and unit["code"] not in ONLY):
            continue
        clear_scene()
        d = unit["outer_mm"]
        obj = build_bin(unit["id"], d["depth"], d["width"], d["height"])
        obj, bar = add_detail(obj, unit["id"], d["depth"], d["width"], d["height"],
                              unit.get("front_bar", False))
        obj.data.materials.clear()
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
        if bar is not None:
            obj = join_parts([obj, bar])
            obj.name = unit["id"]
        results.append((unit["id"], *export_glb(obj, out_dir / f"{unit['id']}.glb")))

    print_summary(results)


if __name__ == "__main__":
    main()
