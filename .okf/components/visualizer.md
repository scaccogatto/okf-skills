---
type: Tool
title: okf_visualize.py
description: Standalone bundle→viz.html renderer (Cytoscape + marked via CDN).
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/visualize/scripts/okf_visualize.py
tags: [python, visualization, cytoscape]
timestamp: "2026-06-28T00:00:00Z"
---

# Overview

The engine behind the [visualize skill](/skills/visualize.md). Parses a bundle
into nodes (concepts, coloured by `type`, sized by body length) and edges
(markdown links), then emits one self-contained HTML file — no backend, nothing
leaves the page.

# Flags

| Flag | Effect |
|------|--------|
| `--title` / `--link` | Name the graph; show a back-link to source. |
| `--layout` | Initial layout (`cose`, `breadthfirst`, `circle`, …). |
| `--og-image` | Emit Open Graph / Twitter Card meta for rich link previews. |

Also supports `?layout=` / `?select=` URL params and deep-linkable concepts
(`viz.html#services/auth-api`).
