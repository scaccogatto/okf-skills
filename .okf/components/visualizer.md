---
type: Tool
title: okf_visualize.py
description: Standalone bundle→viz.html renderer (Cytoscape + marked via CDN).
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/visualize/scripts/okf_visualize.py
tags: [python, visualization, cytoscape]
status: stable
generated: { by: human:scaccogatto, at: "2026-07-27T00:00:00Z" }
---

# Overview

The engine behind the [visualize skill](/skills/visualize.md). Parses a bundle
into nodes (concepts, coloured by `type`, sized by body length) and edges
(markdown links, plus any `sources[].resource` that names another concept in the
bundle), then emits one self-contained HTML file — no backend, nothing leaves the
page. The detail panel renders the v0.2 trust, lifecycle, and provenance
frontmatter: `status`, `generated`, `verified`, `stale_after`, and a Sources list
carrying each source's credibility signals — a `usage_count` shown together with
the `usage_window` that frames it. A v0.1 `timestamp` is read as `generated.at`
so legacy bundles still show a date.

# Derived signals

Two things the panel infers rather than displays, because v0.2 defines them as
derivations and storing them would be storing an opinion:

* the **trust tier** (§5.3) — no `verified` is *unverified*, `verified` by
  non-`human:` actors only is *machine-confirmed*, any `human:` actor makes it
  *human-reviewed*;
* **staleness** (§5.5) — a concept is stale when `today >= stale_after`, which
  absolute dates reduce to a string comparison.

Both are advisory badges, not access control: nothing is hidden or refused on
their account.

# Flags

| Flag | Effect |
|------|--------|
| `--title` / `--link` | Name the graph; show a back-link to source. |
| `--layout` | Initial layout (`cose`, `breadthfirst`, `circle`, …). |
| `--og-image` | Emit Open Graph / Twitter Card meta for rich link previews. |

Also supports `?layout=` / `?select=` URL params and deep-linkable concepts
(`viz.html#services/auth-api`).
