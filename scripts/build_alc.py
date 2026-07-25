"""Generate a GLB model for the attached-lid container (Yosibox T-4641).

Run headless:

    blender --background --python scripts/build_alc.py -- --out build

Axes match the crates: X is the long side, Y the short side, Z height with the
origin at the centre of the base.

The ALC cannot share the eurobox generator, which is why it lives here. Two
differences drive that:

  * The body is tapered rather than straight-walled. An ALC nests when its lid is
    open and stacks when closed, so the draft angle does the job the eurobox's
    stepped foot skirt does.
  * The lid is integral and splits into two leaves along the long axis, each
    hinged on a long side and meeting on the centre line - not a separate SKU as
    it is on the G-family crates.

The 415 mm in the product name is the closed overall height, lid included, so the
body is built to 415 minus the lid thickness rather than to 415.

Hasp tabs sit at the two ends of the lid seam - that is, on the short faces -
because that is where the two leaves meet and where a security seal would go.
Modelled because they are a big part of what makes an ALC recognisable at a
glance; the horizontal rib bands on the walls are not, for the same
fidelity-target reasons as the crate ribbing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boxlib import (clear_scene, cuboid, tapered_box, boolean, bevel_and_smooth,
                    make_material, export_glb, print_summary, load_spec,
                    join_parts)

# --- parameters, millimetres ------------------------------------------------
WALL = 3.0
BASE = 4.5
TAPER = 0.88          # bottom face as a fraction of the top - the nesting draft
BEVEL = 1.5

LID_T = 14.0          # lid leaf thickness
LID_GAP = 3.0         # gap on the centre line between the two leaves
LID_OVERHANG = 4.0    # lid proud of the body on every side

TAB_W = 55.0          # hasp tab across the short face
TAB_D = 14.0          # how far it stands proud
TAB_DROP = 38.0       # how far it hangs below the lid


def build_alc(name, length, width, height):
    body_h = height - LID_T

    body = tapered_box(f"{name}_body", (length, width, body_h),
                       (0, 0, body_h / 2), bottom_scale=TAPER)
    cav = tapered_box(f"{name}_cav",
                      (length - 2 * WALL, width - 2 * WALL, body_h),
                      (0, 0, BASE + body_h / 2), bottom_scale=TAPER)
    boolean(body, cav, "DIFFERENCE")

    parts = [body]

    # two lid leaves, split along the long axis, meeting on the centre line
    half = (width + 2 * LID_OVERHANG) / 2
    leaf_w = half - LID_GAP / 2
    leaf_cy = LID_GAP / 2 + leaf_w / 2
    lid_z = body_h + LID_T / 2
    for sy in (-1, 1):
        parts.append(cuboid(f"{name}_leaf{sy}",
                            (length + 2 * LID_OVERHANG, leaf_w, LID_T),
                            (0, sy * leaf_cy, lid_z)))

        # hasp tabs at both ends of the seam, one per leaf
        for sx in (-1, 1):
            parts.append(cuboid(
                f"{name}_tab{sx}{sy}", (TAB_D, TAB_W, LID_T + TAB_DROP),
                (sx * (length / 2 + LID_OVERHANG + TAB_D / 2 - 1.5),
                 sy * (leaf_cy * 0.42),
                 body_h + LID_T - (LID_T + TAB_DROP) / 2)))

    obj = join_parts(parts)
    bevel_and_smooth(obj, BEVEL)
    obj.name = name
    obj.data.name = name
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path("build")
    repo = Path(__file__).resolve().parent.parent
    out_dir = out if out.is_absolute() else repo / out
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = load_spec(repo)
    blue = tuple(spec["colours"]["alc_blue"]["gltf_base_color_factor_linear"])

    results = []
    for unit in spec["units"]:
        if unit["family"] != "attached_lid_container":
            continue
        clear_scene()
        d = unit["outer_mm"]
        obj = build_alc(unit["id"], d["length"], d["width"], d["height"])
        obj.data.materials.append(make_material("alc_blue", blue))
        results.append((unit["id"], *export_glb(obj, out_dir / f"{unit['id']}.glb")))

    print_summary(results)


if __name__ == "__main__":
    main()
