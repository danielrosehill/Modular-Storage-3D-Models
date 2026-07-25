# Industrial Storage Unit 3D Models (GLB)

Planning and reference repo for producing **GLB** (glTF binary) 3D models of the
industrial storage units in use across our inventory estate — euro stacking
containers, an attached-lid container, and open-front picking bins.

The models are destined for two consumers:

- a **website**, and
- the **WMS app** (bin/location visualisation).

Status: **planning.** Dimensions and colours are documented; no models built yet.

## Units to model

### Euro stacking containers

Solid-walled (Hebrew: *אטום*), straight-wall stacking crates on the VDA 4500
600×400 module. Lids are a separate purchase and are **not** part of the base
product.

| Unit | External L×W×H (mm) | Supplier / SKU | Price | Dimension source |
|---|---|---|---|---|
| Eurobox 60×40×23 | 600 × 400 × 230 | Yosibox — `G-4623`, מק״ט `G47015` | ₪112 inc. VAT (₪95 ex.) | Supplier product page, verified 2026-07-25 |
| Eurobox 40×30×23 | 400 × 300 × 230 | TBD | — | Not yet sourced |
| Eurobox 60×40×31 | 600 × 400 × 310 | TBD | — | Not yet sourced |
| Attached-lid container (ALC) | 600 × 400 × 410 *(footprint inferred)* | TBD | — | Height confirmed; footprint **assumed** |

Generic dimensional data for the 600×400×230 and 600×400×310 sizes already
exists in [`eurobox-standard/specs/`](../eurobox-standard/specs/), alongside the
VDA 4500 source document and a parametric OpenSCAD skeleton.

### Open-front picking bins

Hebrew *אחסונית / ארקלית*. Polypropylene, stackable and shelf-mountable, sold in
minimum quantities of 10. Note that *ארקלית* is a **trade name, not a material** —
these are opaque PP, not acrylic, so they need no transparency in the model.

| Unit | Depth × Width × Height (mm) | Price | Source |
|---|---|---|---|
| Picking bin 1 | 450 × 300 × 210 | ₪57 | Supplier catalogue page, captured 2026-07-25 |
| Picking bin 2 | 295 × 205 × 160 | ₪36 | Supplier catalogue page, captured 2026-07-25 |
| Picking bin 3 | 200 × 145 × 130 | ₪17 | Supplier catalogue page, captured 2026-07-25 |

Hebrew dimension labels map as: *עומק* = depth (front-to-back), *רוחב* = width
(across the open face), *גובה* = height. The supplier lists them in that order,
which is **not** the L×W×H order used for the euroboxes above — a trap when
transcribing.

Machine-readable versions of all of the above: [`specs/units.json`](specs/units.json).

## Colour

"The boxes are blue" turns out to be two distinct blues, sampled from the
supplier product photography on 2026-07-25:

| Family | Sampled sRGB | glTF `baseColorFactor` (linear) |
|---|---|---|
| Euro stacking containers | `#1662DF` – `#0E4CCC` (royal / ultramarine) | `[0.008, 0.122, 0.738]` |
| Picking bins | `#0099DA` – `#039AE1` (bright, cyan-leaning) | `[0.000, 0.319, 0.701]` |

Two things to carry forward:

1. **These are photographic samples, not the plastic's true colour.** Studio
   lighting and JPEG-ish web compression push saturation up. If exactness
   matters, photograph a real box next to a grey card, or ask the suppliers for
   the RAL/Pantone reference.
2. **glTF `baseColorFactor` is linear, not sRGB.** Pasting the hex values
   straight in produces visibly washed-out boxes. The linear column above is
   already converted (`c ≤ 0.04045 ? c/12.92 : ((c+0.055)/1.055)^2.4`).
   Base-colour *textures*, by contrast, are sRGB-encoded and must not be
   pre-converted — only the factor is linear.

## Approach

**Recommendation: model these procedurally, not by scanning.** Polycam is the
wrong tool here, for reasons specific to these two consumers:

- **Dimensions are already known and exact.** Photogrammetry would recover them
  approximately, at best, and needs manual scale-setting afterwards.
- **File size.** A box like this is a few hundred triangles with a single flat
  material — a GLB in the low kilobytes. A Polycam scan is a dense irregular
  mesh plus a texture atlas, realistically 5–30 MB. On a website that difference
  is the whole page budget; in a WMS view showing many bins at once it is fatal.
- **Baked lighting.** Scans bake shadows and highlights into the texture, so the
  boxes look wrong under the app's own lighting and cannot be recoloured.
- **Clean topology** makes it trivial to swap colour per bin type, or to
  instance one mesh hundreds of times in a shelf view.

Scanning only becomes worth it if the site wants photoreal hero imagery with
real-world wear and labels — a different requirement from what's described here.

**Toolchain.** Blender 5.0.1 is installed on this machine and exports GLB
natively, so a headless Python script (`blender --background --python`) can
generate every unit from the numbers in `specs/units.json` in one pass. OpenSCAD
is *not* installed, and the `eurobox-standard` SCAD skeleton exports STL — a
format with **no colour or material support at all**, so an OpenSCAD → STL → GLB
path would still need materials reapplied downstream. That makes Blender the
shorter route despite the existing SCAD work, which remains useful as a
dimensional cross-check.

**Fidelity target.** Correct external dimensions, wall thickness, rounded rim
and corner radii, and the stacking lip/foot — but not the fine external ribbing
visible in the product photos. At the on-screen sizes both consumers will use,
ribs cost geometry and read as noise. Revisit if the website wants close-ups.

## Related repos

- [`eurobox-standard`](../eurobox-standard/) — VDA 4500 source PDF, summary,
  dimension specs, parametric OpenSCAD skeleton.
- [`Yosi-Box-Catalogue`](../Yosi-Box-Catalogue/) / [`yosibox-catalogue`](../yosibox-catalogue/) — Yosibox supplier catalogue; source for the eurobox SKUs.
- [`Israel-Parts-Bins-Research`](../Israel-Parts-Bins-Research/) — picking bin sourcing.
- [`Wheres-My-Stuff-Deployment`](../Wheres-My-Stuff-Deployment/) — the WMS.

## Open questions

1. **ALC footprint** — 600×400 assumed against a confirmed 410 mm height.
2. **Sources for the three unsourced euroboxes** (40×30×23, 60×40×31, ALC), and
   whether they are Yosibox items too, since that would make the blue consistent.
3. **Do lids need modelling?** They are a separate SKU on the euroboxes but
   integral to the ALC. If the WMS ever shows a box as open vs closed, lids want
   to be separate meshes with a hinge origin.
4. **Where do the built GLBs live** — committed here, or published to R2/MinIO
   for the website and WMS to fetch?
5. **Does the WMS need a "fill level" representation** (contents visible inside
   an open box)? That decision drives whether interiors are modelled properly or
   the boxes stay as closed shells.

## Next step

Confirm the ALC footprint and decide on lids, then write the Blender generator
script driven by `specs/units.json`, starting with the Yosibox 60×40×23 as the
reference build.
