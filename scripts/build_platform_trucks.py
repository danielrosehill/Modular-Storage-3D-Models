"""Generate GLB models for folding platform trucks (flatbed trolleys).

    blender --background --python scripts/build_platform_trucks.py -- --out build [--only CODE,CODE]

Family `platform_truck` in specs/units.json. Spec fields used:

    outer_mm      {"length", "width", "height"}  overall in this state (length = deck long side)
    open_height_mm  handle-top height when upright (needed by the folded state)
    deck_mm       {"length", "width"}            steel deck plate
    wheel_d_mm    caster wheel diameter
    deck_top_mm   deck surface height (often not published; see the unit's confidence notes)
    state         "open" (handle up) or "folded" (handle laid over the deck)

Axes: X along the deck (handle at +X), Y across, Z up, origin at the centre of the
footprint on the floor. Unbranded on purpose: the crossbar panel is blank and the
colours are neutral, whatever the reference product looked like.

Not modelled: caster swivel bearings and brakes, mat texture, hinge locking pins.
"""

import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boxlib import (MM, clear_scene, cuboid, bevel_and_smooth, make_material,
                    export_glb, print_summary, load_spec, join_parts)

DECK_T = 25.0          # deck pan depth incl. turned-down edge
MAT_T = 2.0            # rubber mat on the deck
MAT_INSET = 18.0       # visible steel border round the mat
CASTER_INSET = 55.0    # wheel centre in from the deck edge
WHEEL_W = 32.0
FORK_T = 4.0
TUBE_D = 25.0          # handle tube
HINGE_UP = 40.0        # hinge axis above the deck top
HANDLE_IN = 22.0       # handle uprights in from the deck side edge
PANEL_H = 90.0         # blank crossbar panel
PANEL_FRAC = 0.62      # panel height up the handle, as a fraction
ROD_D = 12.0           # rod joining the hinge brackets

FRAME_RGB = (0.30, 0.32, 0.34)     # neutral powder-coated grey
MAT_RGB = (0.03, 0.03, 0.03)
TYRE_RGB = (0.05, 0.05, 0.05)
HUB_RGB = (0.55, 0.57, 0.6)
ZINC_RGB = (0.62, 0.64, 0.66)


def cyl(name, d, length, loc, axis):
    rot = {"x": (0, math.radians(90), 0), "y": (math.radians(90), 0, 0), "z": (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=d / 2 * MM, depth=length * MM,
                                        location=tuple(c * MM for c in loc), rotation=rot)
    o = bpy.context.active_object
    o.name = name
    return o


def with_mat(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj


def rotate_about_y(objs, pivot_x, pivot_z, angle_deg):
    """Rotate objects rigidly about a Y-parallel axis through (pivot_x, pivot_z) mm.
    Positive angle swings +Z toward -X (a handle folding forward over the deck).
    (A parent-empty version mapped Z to Y instead of X: 2026-11-18. Use the matrix.)"""
    from mathutils import Matrix
    bpy.context.view_layer.update()
    t = Matrix.Translation((pivot_x * MM, 0, pivot_z * MM))
    # Blender's +Y rotation takes +Z toward +X, so negate for "forward" (-X)
    r = t @ Matrix.Rotation(-math.radians(angle_deg), 4, "Y") @ t.inverted()
    for o in objs:
        o.matrix_world = r @ o.matrix_world
    bpy.context.view_layer.update()
    if "--debug" in sys.argv:
        for o in objs:
            ws = [o.matrix_world @ v.co for v in o.data.vertices]
            print("DBG", o.name, "y", round(min(w.y for w in ws) / MM), round(max(w.y for w in ws) / MM), "x", round(min(w.x for w in ws) / MM), round(max(w.x for w in ws) / MM),
                  round(min(w.z for w in ws) / MM), round(max(w.z for w in ws) / MM))


def build(unit, mats):
    o = unit["outer_mm"]
    deck = unit["deck_mm"]
    L, W = deck["length"], deck["width"]
    H = unit.get("open_height_mm", o["height"])   # handle top when upright
    wd = unit["wheel_d_mm"]
    top = unit["deck_top_mm"]
    folded = unit.get("state") == "folded"
    parts = []

    # deck pan + mat
    parts.append(with_mat(cuboid("deck", (L, W, DECK_T), (0, 0, top - DECK_T / 2)), mats["frame"]))
    parts.append(with_mat(cuboid("mat", (L - 2 * MAT_INSET, W - 2 * MAT_INSET, MAT_T),
                                 (0, 0, top + MAT_T / 2 - 0.5)), mats["mat"]))

    # casters: top plate, two fork legs, wheel with hub
    under = top - DECK_T
    axle_z = wd / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (L / 2 - CASTER_INSET), sy * (W / 2 - CASTER_INSET)
            parts.append(with_mat(cuboid("cplate", (70, 60, FORK_T), (cx, cy, under - FORK_T / 2)), mats["zinc"]))
            leg_h = under - FORK_T - axle_z + 10
            for side in (-1, 1):
                parts.append(with_mat(cuboid("fork", (36, FORK_T, leg_h),
                                             (cx, cy + side * (WHEEL_W / 2 + FORK_T / 2 + 1),
                                              under - FORK_T - leg_h / 2)), mats["zinc"]))
            parts.append(with_mat(cyl("tyre", wd, WHEEL_W, (cx, cy, axle_z), "y"), mats["tyre"]))
            parts.append(with_mat(cyl("hub", wd * 0.55, WHEEL_W + 2, (cx, cy, axle_z), "y"), mats["hub"]))

    # hinge brackets + rod at the +X end
    hx = L / 2 - 30
    hz = top + HINGE_UP
    yy = W / 2 - HANDLE_IN
    for sy in (-1, 1):
        parts.append(with_mat(cuboid("hinge", (60, 6, HINGE_UP + 30),
                                     (hx, sy * (yy + TUBE_D / 2 + 4), top + (HINGE_UP + 30) / 2)), mats["zinc"]))
    parts.append(with_mat(cyl("rod", ROD_D, 2 * yy + 20, (hx - 20, 0, top + 25), "y"), mats["zinc"]))

    # handle: two uprights, top bar, blank crossbar panel (built upright, folded after)
    handle = []
    up_len = H - hz - TUBE_D / 2
    for sy in (-1, 1):
        handle.append(with_mat(cyl("upright", TUBE_D, up_len, (hx, sy * yy, hz + up_len / 2), "z"), mats["frame"]))
    handle.append(with_mat(cyl("topbar", TUBE_D, 2 * yy + TUBE_D, (hx, 0, H - TUBE_D / 2), "y"), mats["frame"]))
    pz = hz + PANEL_FRAC * up_len
    handle.append(with_mat(cuboid("panel", (4, 2 * yy, PANEL_H), (hx, 0, pz)), mats["frame"]))
    if folded:
        # lay the handle forward over the deck (toward -X)
        rotate_about_y(handle, hx, hz, 90)
    parts += handle

    for p in parts:
        if p.name.startswith(("deck", "hinge", "panel", "cplate")):
            bevel_and_smooth(p, 1.0)
    obj = join_parts(parts)
    obj.name = unit["id"]
    obj.data.name = unit["id"]
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path("build")
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    repo = Path(__file__).resolve().parent.parent
    out_dir = out if out.is_absolute() else repo / out
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = load_spec(repo)

    results = []
    for unit in spec["units"]:
        if unit["family"] != "platform_truck" or (only and unit["code"] not in only):
            continue
        clear_scene()
        mats = {"frame": make_material("frame_grey", FRAME_RGB, 0.45, 0.3),
                "mat": make_material("rubber_mat", MAT_RGB, 0.9),
                "tyre": make_material("tyre", TYRE_RGB, 0.85),
                "hub": make_material("hub", HUB_RGB, 0.4),
                "zinc": make_material("zinc", ZINC_RGB, 0.35, 0.8)}
        obj = build(unit, mats)
        results.append((unit["id"], *export_glb(obj, out_dir / f"{unit['id']}.glb")))
    print_summary(results)


if __name__ == "__main__":
    main()
