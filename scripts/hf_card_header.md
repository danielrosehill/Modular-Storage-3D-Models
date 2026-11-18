---
license: cc-by-4.0
pretty_name: Modular Storage 3D Models
tags:
  - 3d
  - glb
  - gltf
  - obj
  - dxf
  - cad
  - revit
  - warehouse
  - logistics
  - storage
  - eurobox
  - industrial
  - low-poly
  - 3d-assets
  - storage-planning
  - picking-bins
  - tilt-bins
  - totes
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files:
      - split: train
        path:
          - metadata.jsonl
          - models/**/*.jpg
---

# Modular Storage 3D Models

True-scale, low-poly **GLB** (glTF 2.0) models of standard industrial storage
units: euro stacking containers (600 × 400 mm module) and their US straight-wall
equivalents, attached-lid containers, open-front picking bins, tilt-out bin units
and a boltless shelving bay. Metric (Israel/EU) and US catalogue sizes. Every
model is generated from a dimension spec by headless Blender scripts, so the
dimensions are the spec, not an eyeballed mesh.

- **Interactive 3D viewer:** [3D Assets Viewer](https://huggingface.co/spaces/danielrosehill/3D-Assets-Viewer) (search, filter, orbit any model, download)
- **Source, generators and specs:** <https://github.com/danielrosehill/Modular-Storage-3D-Models>
- **Also on Sketchfab** (in-browser 3D viewer): the
  [Industrial Storage](https://sketchfab.com/danielrosehill/collections/industrial-storage) collection

## Metadata (`metadata.jsonl`, one row per model)

| Column | Meaning |
|---|---|
| `id` | Unique, stable slug (also the generator's build name) |
| `code` | Short unique code used in folder names (`EU6423`, `TB603O` ...) |
| `name`, `description` | Display name; one-paragraph description |
| `category` | `modular-storage` or `shelving` |
| `subcategory` | `open-top-totes`, `closed-totes`, `picking-bins`, `tilt-bin-units`, `boltless-shelving` |
| `family` | Generator family (finer than subcategory) |
| `colour`, `colour_hex` | Colour as modelled; sampled sRGB hex of the real moulding where known |
| `material` | Plastic / steel / acrylic as modelled |
| `lid` | Lid arrangement (`none`, attached hinged ...) |
| `access` | `open-top`, `open-front`, `tilt-out`, `lidded`, `open` |
| `state` | `open` / `closed` for models with a moving part, else `n/a` |
| `open_deg` | Tilt angle of open variants (assumed 35°, not measured) |
| `cells` | Bins per tilt-bin unit |
| `stackable`, `nestable` | Booleans |
| `region` | `metric` (Israel/EU sizes) or `US` (inch catalogue sizes) |
| `footprint_mm`, `outer_mm`, `outer_in` | External dimensions; inches for US units as published |
| `external_volume_l` | External bounding volume in litres. **Not** usable capacity |
| `reference_product`, `source`, `dimension_confidence` | Where the dimensions come from and how sure they are |
| `triangles`, `vertices`, `file_bytes` | Read from the GLB |
| `glb`, `obj`, `dxf`, `file_name` | Paths to the model in each format and its preview image |
| `sketchfab_url`, `license` | 3D web view; licence per row |

## Layout

| Path | Contents |
|---|---|
| `models/<CODE>/<CODE>.glb` | The asset, at true scale in metres |
| `models/<CODE>/<CODE>.obj` + `.mtl` | OBJ, metres, Y-up: Rhino, SketchUp, Blender and most 3D tools |
| `models/<CODE>/<CODE>.dxf` | DXF (R2018) polyface mesh, **millimetres**, Z-up: Revit / Revit LT (Insert → Import CAD) and AutoCAD, which cannot open GLB |
| `models/<CODE>/<CODE>.jpg` | Preview render |
| `models/<CODE>/description.txt` | Description, dimensions and sources |
| `metadata.jsonl` | One row per unit: code, family, region, `outer_mm`, `outer_in`, cells, reference product, GLB path, Sketchfab URL |
| `units.json` | The full generator spec (colours, geometry notes, sources, confidence) |

The dataset viewer shows the preview images with the metadata as columns; it
cannot render GLB. Download one model:

```bash
hf download danielrosehill/Modular-Storage-3D-Models models/EU6423/EU6423.glb --repo-type dataset --local-dir .
```

## Licence

CC BY 4.0. Attribution: "Modular Storage 3D Models" by Daniel Rosehill.
