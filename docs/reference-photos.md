# Reference photography

Source URLs for the Yosibox product photography used as geometry reference when
modelling. Links only — the images themselves are Yosibox's commercial product
photography and are **not** vendored into this public repo. See the note at the
bottom.

All URLs verified 2026-07-25. They are served from Yosibox's CloudFront
distribution and follow the pattern:

```
https://d3m9l0v76dty0.cloudfront.net/system/photos/<photo-id>/<size>/<hash>.png
```

`<size>` is one of `thumb`, `medium`, `large`, `original`. Substituting
`original` gets the full-resolution asset, which is what the IDs below assume.

## Finding the product photos on a page

Worth recording, because it is not obvious: a Yosibox item page references
roughly 35–40 CloudFront photos, but only 2–7 of them are the product. The rest
are shared site furniture — banners, payment icons, trust badges — and are
byte-identical across every item page. The reliable way to isolate the product
shots is to fetch two or more item pages and **take the set difference** of
their photo IDs. Filtering by ID range also works in practice (product photos
are in the 17M–20M range, site chrome in the 100K–1M range) but is incidental
rather than guaranteed.

The `og:image` meta tag gives the primary product shot only, and the embedded
`application/ld+json` Product block carries name, price and currency — but its
`sku` and `mpn` fields are null on every page checked, so the SKU has to come
from the title.

## Eurobox `G-3415` — 400×300×150

- `18111070` / `09a4a22e2243c7e98d99c19fd28948e6.png` — 3780×1890 (primary)
- `18111072` / `51419056bdcc097eefe668b6ca8f22a4.png` — 3780×1890
- `18111074` / `0e5ddf9b24c2ba85ff13352f2169d4ac.png` — 1414×2000

## Eurobox `G-4623` — 600×400×230

- `18129746` / `23dfeca12aa5cc584de0595d6e978f5d.png` — 3780×1890 (primary)
- `18129749` / `5f3811e5cfc484f1d87b2ca435d9b1b3.png` — 3780×1890

## Eurobox `G-4634` — 600×400×340

- `18200831` / `5b121867c38ed606f0121e43d3fa57ab.png` — 3780×1890 (primary)
- `18200832` / `0954f437fbd0c27594ad2c95f3bb4ce2.png` — 3780×1890 — **near-orthographic front elevation, the most useful single reference we have**
- `18200833` / `d8d16d5b1aafbee80990da676894d466.png` — 3780×1890
- `20372855` / `e88519cab720141d998e9bc9c99915c2.png` — 1080×1080
- `20372856` / `55c5c1b3e267153c8437d49646c87cc8.png` — 1080×1080

## ALC `T-4641` — 600×400×415

- `17800782` / `944b7e5345c4551e8ee1b27a846f8095.png` — 1414×2000
- `17800783` / `c4b4e646d4408c3af44184cb34cf5a57.png` — 1414×2000
- `17800784` / `1c9167f7c3c22965136e07b5c857da8d.png` — 1414×2000
- `17800785` / `0e73c1cb663ea9affc72b8fc1bc41197.png` — 1414×2000
- `17800786` / `ed74ee71fd7142fa76876b0cce2c3495.png` — 1414×2000
- `17906748` / `553c7c1e261261f4969824a45adac3a9.png` — 1376×1574 (primary)
- `18249286` / `ce857f1e7baa2bfdad008954f5d50d0f.png` — 3780×1890

## Geometry read off these photos

From the `G-4634` front elevation (`18200832`), features shared by the G-family
crates:

- Oval **handle cutouts** through the top rim, one near each end of the long side.
- A **rib grid** on the upper band of the wall — roughly square cells between the
  rim and the mid-height line.
- **Vertical rib columns** at the corners and at intervals along the wall.
- A **recessed centre panel** on the lower half, smooth and unribbed — the
  natural place for a label.

None of this is in the fidelity target (see the main README) but it is what a
higher-detail pass would need to add.

## On vendoring the images

These are Yosibox's copyrighted commercial product photographs. This repo is
public, so they are referenced by URL rather than committed. If they are ever
copied in, do it deliberately: attribute Yosibox, note that they are used as
dimensional reference under fair-dealing-style reasoning, and keep them to a
curated handful rather than whole galleries. Photographs taken of our own
purchased units carry none of this friction and are the better long-term answer.
