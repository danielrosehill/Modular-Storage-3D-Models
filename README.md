# Storage Box 3D Models (GLB)

Planning repo for producing **GLB** (glTF binary) 3D models of the logistic
storage boxes in use across the inventory estate — three eurobox sizes plus one
attached-lid container — each rendered in a distinct colour.

Status: **planning only.** No models produced yet.

## Scope — the four boxes

| # | Box | External L×W×H (mm) | Footprint | Colour | Dimension source |
|---|---|---|---|---|---|
| 1 | Eurobox, low | 600 × 400 × 230 | 600×400 | TBD | [`eurobox-standard/specs/eurobox-600x400x230.json`](../eurobox-standard/specs/eurobox-600x400x230.json) |
| 2 | Eurobox, half-footprint | 400 × 300 × 230 | 400×300 | TBD | no spec yet — needs adding |
| 3 | Eurobox, tall | 600 × 400 × 310 | 600×400 | TBD | [`eurobox-standard/specs/eurobox-600x400x310.json`](../eurobox-standard/specs/eurobox-600x400x310.json) |
| 4 | Attached-lid container (ALC) | 600 × 400 × 410 *(assumed footprint)* | 600×400 | TBD | needs a supplier datasheet |

Notes on the table:

- Sizes 1–3 are all VDA 4500 footprints (600×400 and 400×300 are both
  sub-modules of the 1200×800 Euro pallet), so they can very likely come from
  **one parametric model** driven by L/W/H rather than three separate builds.
- Box 4 is a different animal: an attached-lid container has an integrated
  hinged two-part lid, so it needs lid geometry sizes 1–3 don't have. The
  **41 cm height is confirmed; the 600×400 footprint is inferred** — needs
  confirming before modelling.
- All heights above are treated as *external overall* height. Eurobox spec
  sheets sometimes quote internal depth instead, which for a 230 mm box is
  nearer 210 mm. Worth pinning down which figure the source used.

## Colour scheme

The whole point of the exercise is colour-differentiated boxes, so the palette
is a first-class decision, not a finishing touch. Undecided:

- One flat colour per box **type**, or per **location/zone**, or per
  **contents category**?
- Do the colours need to match the physical boxes already bought, or is this a
  free choice for the digital representation?
- Should the model carry a separate material for the label panel so a bin ID
  can be textured on later?

In glTF terms a flat colour is cheapest as a `pbrMetallicRoughness` base colour
factor with no texture at all — a few hundred bytes. That stays true only if
each box is a single material; per-face colouring forces either vertex colours
or a texture atlas.

## Related repos

- [`eurobox-standard`](../eurobox-standard/) — VDA 4500 source PDF, summary,
  the two JSON dimension specs, and **parametric OpenSCAD skeletons**
  (`cad/eurobox.scad`). The most likely starting point: parameterise the SCAD
  model over the three eurobox sizes, export mesh, convert to GLB.
- [`Yosi-Box-Catalogue`](../Yosi-Box-Catalogue/) / [`yosibox-catalogue`](../yosibox-catalogue/) — supplier catalogue data; likely source for the ALC datasheet.
- [`Israel-Parts-Bins-Research`](../Israel-Parts-Bins-Research/) — small parts bin sourcing.
- [`Wheres-My-Stuff-Deployment`](../Wheres-My-Stuff-Deployment/) — the WMS, a
  plausible consumer of the models.

## Open questions

1. **What consumes the GLBs?** Web viewer, WMS bin visualisation, AR placement,
   packing/load simulation, or render stills for documentation. This sets the
   polygon and texture budget and whether real-world metre scale matters.
2. **ALC footprint** — 600×400×410 assumed; confirm against the actual product.
3. **Fidelity** — schematic block with correct external dimensions and rounded
   corners, or true-to-life with ribs, handles, stacking rims, lid lips?
4. **Are lids needed** on the eurobox sizes too, and if so as separate meshes
   (so they can be shown open/closed) or fused?
5. **Interior geometry** — hollow with modelled wall thickness, or solid shell?
   Matters if anything ever needs to show contents inside.
6. **Route to GLB** — OpenSCAD → STL → GLB, Blender, or a generative 3D service.
7. **Where do the GLBs live** once built — in this repo, or published to R2/
   MinIO for the consuming app to fetch?

## Next step

Answer Q1 and Q2; then decide parametric-vs-hand-modelled and start with size 1
as the reference build.
