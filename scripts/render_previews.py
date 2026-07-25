"""Render a three-quarter preview PNG for each GLB in build/.

    blender --background --python scripts/render_previews.py -- --in build --out build/previews

Exists because an export can succeed while the geometry is wrong - a boolean that
silently fails still writes a valid GLB. Rendering is the cheapest way to see
whether the cavity, foot skirt and handle cutouts actually cut.

Cycles on CPU, because headless EEVEE needs a GL context this box does not have
in background mode.
"""

import bpy
import sys
import math
from pathlib import Path
from mathutils import Vector


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def frame_object(obj, camera):
    """Point the camera at the object and back off until it fits."""
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    centre = sum(bb, Vector()) / 8
    radius = max((v - centre).length for v in bb)
    # Look from -X. The picking bins have their open face at -X, so a camera on
    # +X renders them as a featureless slab and hides the whole point of the
    # model. The euroboxes are labelled on all four walls, so the same view
    # suits them equally well.
    direction = Vector((-1.0, -1.25, 0.8)).normalized()
    camera.location = centre + direction * (radius * 3.1)
    track = camera.constraints.new(type="TRACK_TO")
    empty = bpy.data.objects.new("target", None)
    bpy.context.collection.objects.link(empty)
    empty.location = centre
    track.target = empty


def setup_world():
    world = bpy.data.worlds.new("w")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    # keep this low. A bright environment plus a strong key light blows the
    # base colour out to a pale periwinkle and makes the model look like it has
    # the wrong material, which is misleading when the whole point of the
    # preview is to check the model.
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.35


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    repo = Path(__file__).resolve().parent.parent
    in_dir = repo / (argv[argv.index("--in") + 1] if "--in" in argv else "build")
    out_dir = repo / (argv[argv.index("--out") + 1] if "--out" in argv
                      else "build/previews")
    out_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.image_settings.file_format = "PNG"

    for glb in sorted(in_dir.glob("*.glb")):
        clear_scene()
        setup_world()
        bpy.ops.import_scene.gltf(filepath=str(glb))
        objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        if not objs:
            print(f"!! no mesh in {glb.name}")
            continue
        obj = objs[0]

        cam_data = bpy.data.cameras.new("cam")
        cam = bpy.data.objects.new("cam", cam_data)
        bpy.context.collection.objects.link(cam)
        scene.camera = cam
        frame_object(obj, cam)

        light_data = bpy.data.lights.new("key", type="AREA")
        light_data.energy = 140
        light_data.size = 3.0
        light = bpy.data.objects.new("key", light_data)
        bpy.context.collection.objects.link(light)
        light.location = (1.2, -1.4, 2.0)
        light.rotation_euler = (math.radians(30), math.radians(12), 0)

        scene.render.filepath = str(out_dir / f"{glb.stem}.png")
        bpy.ops.render.render(write_still=True)
        print(f"rendered {glb.stem}")


if __name__ == "__main__":
    main()
