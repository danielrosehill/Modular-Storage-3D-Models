# Industrial Storage Unit 3D Models (GLB)

Planning and reference repo for producing **GLB** (glTF binary) 3D models of the
industrial storage units in use across our inventory estate — euro stacking
containers, an attached-lid container, and open-front picking bins.

The models are destined for two consumers:

- a **website**, and
- the **WMS app** (bin/location visualisation).

Status: **planning.** Dimensions and suppliers are documented; no models built yet.

## Units to model

### Euro stacking containers

Solid-walled (Hebrew: *אטום*), straight-wall stacking crates on the VDA 4500
600×400 module. Lids are a separate purchase and are **not** part of the base
product.

| Unit | External L×W×H (mm) | Supplier / SKU | Price | Dimension source |
|---|---|---|---|---|
| Eurobox 60×40×23 | 600 × 400 × 230 | Yosibox — `G-4623`, מק״ט `G47015` | ₪112 inc. VAT (₪95 ex.) | Supplier product page, verified 2026-07-25 |
| Eurobox 40×30×23 | 400 × 300 × 230 | TBD | — | Not yet sourced |
| Eurobox 60×40×31 | 600 × 400 × 310 | TBD — try `G-4631` (see below) | — | Not yet sourced |

Generic dimensional data for the 600×400×230 and 600×400×310 sizes already
exists in [`eurobox-standard/specs/`](../eurobox-standard/specs/), alongside the
VDA 4500 source document and a parametric OpenSCAD skeleton.

**Yosibox SKU pattern (inferred, not confirmed).** `G-4623` is the 60×40×23 and
`T-4641` is the 60×40×41.5, which reads as `<letter>-<40/60 footprint><height in
cm>`. If that holds, the 60×40×31 should be near `G-4631`. Worth trying before
searching the catalogue by hand — but it is a pattern extrapolated from two data
points, so treat it as a lead, not a fact.

### Attached-lid container (ALC)

| Unit | External L×W×H (mm) | Supplier / SKU | Price | Dimension source |
|---|---|---|---|---|
| ALC 60×40×41.5 | 600 × 400 × **415** | Yosibox — `T-4641`, מק״ט `T04` | ₪155 inc. VAT (₪131 ex.) | Supplier product page, verified 2026-07-25 |

Confirmed geometry from the product photography, and it differs from the
euroboxes in ways that matter for modelling:

- **Integral two-part hinged lid** (*עם מכסה*) that meets along the centre line,
  with interlocking tabs — not a separate SKU as with the euroboxes.
- **Front hasp tabs** on the lid edge for a security seal.
- **Tapered body** with horizontal rib bands, so the containers **nest** when the
  lid is open and **stack** when it is closed. The taper means this is not a
  scaled-up eurobox and cannot share the straight-wall parametric model.
- Height is **415 mm**, not the 410 mm originally assumed.

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

All units are blue. Beyond that, **the supplier photography cannot tell us how
blue**, and this is worth stating clearly because it is easy to be fooled by it.

Sampled values, all from supplier product photos on 2026-07-25:

| Family | Sampled sRGB range |
|---|---|
| Euro stacking containers | `#0E4CCC` – `#1662DF` |
| ALC | `#06549C` (shadowed face) – `#11A4F1` (lit face) – `#34CAFD` (lid top) |
| Picking bins | `#0099DA` – `#039AE1` |

The ALC row is the tell. Those three samples are **the same piece of blue
polypropylene** under different lighting, and they span a wider range than the
gap between any two families in the table. So the apparent differences between
families are within the noise floor of the method, and my earlier read that the
euroboxes and picking bins are two distinctly different blues was overstated —
the photos do not support that conclusion either way.

The same applies to the ALC lid, which looks like a brighter cyan than its body
in every photo. That is exactly what an upward-facing surface does under overhead
studio lighting, so it is most likely one colour, not a two-tone moulding.

Practical consequences:

1. **Do not author materials from these hex values.** Get the RAL or Pantone
   reference from Yosibox and the bin supplier, or photograph a real unit beside
   a grey card. Until then, model with a single shared blue and treat per-family
   colour as an open question.
2. **glTF `baseColorFactor` is linear, not sRGB.** Whatever value is settled on,
   pasting the hex straight in produces visibly washed-out boxes; convert first
   (`c ≤ 0.04045 ? c/12.92 : ((c+0.055)/1.055)^2.4`). Base-colour *textures*, by
   contrast, are sRGB-encoded and must not be pre-converted — only the factor is.

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
  boxes look wrong under the app's own lighting and cannot be recoloured — and,
  per the colour section above, the baked-in lighting is severe enough to make
  the plastic look like three different blues.
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

**Three geometry families, not one generator.** The straight-wall euroboxes
share a parametric model driven by L/W/H. The ALC needs its own (taper, hinged
lid, hasp tabs). The picking bins need a third (open front, tapered nesting
body, front lip). Budget the work accordingly.

**Fidelity target.** Correct external dimensions, wall thickness, rounded rim
and corner radii, and the stacking lip/foot — but not the fine external ribbing
visible in the product photos. At the on-screen sizes both consumers will use,
ribs cost geometry and read as noise. Revisit if the website wants close-ups.

## Related repos

- [`eurobox-standard`](../eurobox-standard/) — VDA 4500 source PDF, summary,
  dimension specs, parametric OpenSCAD skeleton.
- [`Yosi-Box-Catalogue`](../Yosi-Box-Catalogue/) / [`yosibox-catalogue`](../yosibox-catalogue/) — Yosibox supplier catalogue; source for the eurobox and ALC SKUs.
- [`Israel-Parts-Bins-Research`](../Israel-Parts-Bins-Research/) — picking bin sourcing.
- [`Wheres-My-Stuff-Deployment`](../Wheres-My-Stuff-Deployment/) — the WMS.

## Open questions

1. **Actual colour references** from both suppliers — see the colour section.
2. **Sources for the two unsourced euroboxes** (40×30×23 and 60×40×31); the SKU
   pattern above is a starting point for the latter.
3. **Do the eurobox lids need modelling?** They are a separate SKU. The ALC's is
   integral, and if the WMS ever shows open vs closed it wants to be a separate
   mesh with a hinge origin — two hinge origins, in the ALC's case.
4. **Where do the built GLBs live** — committed here, or published to R2/MinIO
   for the website and WMS to fetch?
5. **Does the WMS need a "fill level" representation** (contents visible inside
   an open box)? That decision drives whether interiors are modelled properly or
   the boxes stay as closed shells.

## Next step

Write the Blender generator for the straight-wall eurobox family first, driven by
`specs/units.json`, using the Yosibox 60×40×23 as the reference build. The ALC
and picking bin generators follow as separate pieces of work.
