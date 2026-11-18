# /// script
# dependencies = ["trimesh>=4", "ezdxf>=1.3", "numpy"]
# ///
"""Add CAD-friendly copies next to each GLB in a dataset tree.

    uv run scripts/export_cad.py hf-dataset/models

For every <dir>/<CODE>/<CODE>.glb writes, in the same folder:

  <CODE>.obj (+ .mtl)  metres, Y-up as glTF. Rhino, SketchUp, Blender, most 3D tools.
  <CODE>.dxf           DXF R2018, polyface meshes, MILLIMETRES ($INSUNITS=4), Z-up.
                       For Revit / Revit LT (Insert > Import CAD) and AutoCAD, which
                       cannot open GLB. One layer per material.

Called by build_hf_dataset.py; no Blender needed.
"""
import sys
from pathlib import Path

import ezdxf
import numpy as np
import trimesh


def convert(glb: Path):
    code = glb.stem
    scene = trimesh.load(glb, force="scene")
    obj_text, files = trimesh.exchange.obj.export_obj(
        scene, include_texture=True, return_texture=True, mtl_name=f"{code}.mtl")
    (glb.parent / f"{code}.obj").write_text(obj_text)
    for name, data in files.items():
        (glb.parent / name).write_bytes(data)

    doc = ezdxf.new("R2018", units=4)                    # 4 = millimetres
    msp = doc.modelspace()
    for i, geom in enumerate(scene.dump()):              # node transforms applied
        v = np.asarray(geom.vertices) * 1000.0           # m -> mm
        v = v[:, [0, 2, 1]] * np.array([1.0, -1.0, 1.0])  # glTF Y-up -> CAD Z-up
        layer = f"{code}-{i}"
        doc.layers.add(layer)
        pf = msp.add_polyface(dxfattribs={"layer": layer})
        pf.append_faces([[tuple(v[j]) for j in f] for f in geom.faces])
        pf.optimize()
    doc.saveas(glb.parent / f"{code}.dxf")


def main():
    root = Path(sys.argv[1])
    glbs = sorted(root.glob("*/*.glb"))
    for g in glbs:
        convert(g)
    print(f"cad: {len(glbs)} models -> obj + dxf")


if __name__ == "__main__":
    main()
