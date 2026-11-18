---
license: cc-by-4.0
pretty_name: Modular Storage 3D Models
tags:
  - 3d
  - glb
  - gltf
  - warehouse
  - logistics
  - storage
  - eurobox
  - industrial
  - low-poly
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

## Layout

| Path | Contents |
|---|---|
| `models/<CODE>/<CODE>.glb` | The asset, at true scale in metres |
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
