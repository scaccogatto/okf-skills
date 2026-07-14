---
type: Decision
title: Scale guardrails in the visualizer
description: Default to a linear layout above 1k concepts, warn above 5k, batch and debounce filtering.
tags: [adr, performance]
timestamp: "2026-07-14T00:00:00Z"
---

# Context

Measured in Chrome against synthetic bundles, the default force (cose) layout
blocked the page for ~32 s at ~2k concepts (its cost grows roughly quadratically
with node count — 20k+ extrapolates to hours), while the linear layouts loaded
the same bundle in under 2 s. Independently of layout, a 23k-concept page took
~27 s to load with ~650 MB of heap, and the unbatched per-keystroke filter pass
cost ~1.8 s. Real bundles are curated and small, but nothing stopped the
[visualizer](/components/visualizer.md) from generating a page that freezes the
viewer's browser.

# Decision

Keep force as the default layout only up to 1,000 concepts and fall back to the
linear `concentric` layout above that; an explicit `--layout` (or `?layout=`)
always wins, and the in-page layout picker asks for confirmation before running
force on a large graph. Above 5,000 concepts, print a warning suggesting a
subtree render (the [visualize skill](/skills/visualize.md) accepts any
directory). Wrap filter passes in `cy.batch()` and debounce the search box. A
new `--max-nodes` flag lets CI refuse oversized bundles outright.

# Consequences

* Small bundles render exactly as before; large bundles stay responsive instead
  of freezing the tab.
* The guardrails are defaults, not caps — force layout remains available at any
  size for whoever explicitly asks.
* Legibility past ~5k concepts is still poor by nature; subtree rendering is
  the documented path, not something the tool tries to solve.
