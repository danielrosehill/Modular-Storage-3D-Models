"""Shared Blender helpers for the storage unit generators.

Everything here takes millimetres and emits metres, because the specs are in mm
and glTF expects metres. Keeping the conversion in one place means no generator
has to remember to do it.

Meshes are built from explicit vertices rather than by scaling a primitive, so
every object leaves this module with a scale of 1. Non-uniform object scale
survives boolean modifiers but interacts badly with bevel width, which is
measured in local space - a 600x400x230 crate built by scaling a unit cube gets
visibly different edge radii on each axis.
"""

import bpy
import bmesh
import math
from pathlib import Path

MM = 0.001


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def tapered_box(name, size, centre, bottom_scale=1.0, rotation=None):
    """Box with an optionally smaller bottom face. Sizes/centre in mm.

    bottom_scale < 1 gives the draft angle that lets nesting bins stack into one
    another; at 1.0 this is a plain cuboid.
    """
    sx, sy, sz = (s * MM for s in size)
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    b = bottom_scale
    verts = [
        (-hx * b, -hy * b, -hz), (hx * b, -hy * b, -hz),
        (hx * b, hy * b, -hz), (-hx * b, hy * b, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = tuple(c * MM for c in centre)
    if rotation:
        obj.rotation_euler = rotation

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    return obj


def cuboid(name, size, centre, rotation=None):
    return tapered_box(name, size, centre, 1.0, rotation)


def boolean(target, cutter, operation):
    mod = target.modifiers.new(name=f"bool_{cutter.name}", type="BOOLEAN")
    mod.object = cutter
    mod.operation = operation
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def bevel_and_smooth(obj, width_mm, segments=2, angle_deg=30, smooth_deg=40):
    bpy.context.view_layer.objects.active = obj
    bev = obj.modifiers.new(name="bevel", type="BEVEL")
    bev.width = width_mm * MM
    bev.segments = segments
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(angle_deg)
    bpy.ops.object.modifier_apply(modifier=bev.name)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth_deg))


def make_material(name, linear_rgb, roughness=0.42, metallic=0.0):
    """linear_rgb goes straight into glTF baseColorFactor, which is also linear.

    Do not pass sRGB hex values converted by eye - see the colour section of the
    README.
    """
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:          # avoids the use_nodes setter, which is
        mat.use_nodes = True           # deprecated for removal in Blender 6.0
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*linear_rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def join_parts(parts):
    """Join a list of objects into the first one and return it."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    return parts[0]


def export_glb(obj, path: Path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB",
                              use_selection=True)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    return tris, len(obj.data.vertices), path.stat().st_size


def print_summary(results):
    print("\n=== build summary ===")
    for name, tris, verts, size in results:
        print(f"{name:26s} {tris:6d} tris  {verts:6d} verts  {size/1024:7.1f} KB")


def load_spec(repo: Path):
    import json
    return json.loads((repo / "specs" / "units.json").read_text(encoding="utf-8"))
