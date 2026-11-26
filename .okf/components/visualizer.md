---
type: Tool
title: okf_visualize.py
description: Standalone bundle to viz.html renderer (Cytoscape, marked, DOMPurify via CDN).
resource: https://github.com/ekar-is/okf-skills/blob/main/skills/visualize/scripts/okf_visualize.py
tags: [python, visualization, cytoscape]
status: stable
generated: { by: "claude/opus-5.5", at: "2026-11-26T00:00:00Z" }
---

# Overview

The engine behind the [visualize skill](/skills/visualize.md). Parses a bundle
into nodes (concepts, coloured by `type`, sized by body length) and edges
(markdown links, plus any `sources[].resource` that names another concept in the
bundle), then emits one self-contained HTML file — no backend, nothing leaves the
page. The detail panel renders the v0.3 trust, lifecycle, and provenance
frontmatter: `status` (an unknown value gets its own badge), `generated`,
`verified`, `stale_after`, a `superseded_by` link, and a Sources list carrying
each source's credibility signals (a `usage_count` shown together with the
`usage_window` that frames it). A v0.1 `timestamp` is read as `generated.at` so
legacy bundles still show a date.

Nodes follow §3.2 discovery: only a `.md` with frontmatter and a `type` is a
concept, so there are no more Untyped nodes. Edges come from markdown links, from
bundle-internal `sources[].resource`, and from path-valued frontmatter fields
(§6.4), all resolved with the §6 rule.

Concept bodies are untrusted content, so markdown output is passed through
DOMPurify before it reaches `innerHTML`.

The three CDN scripts (Cytoscape, marked, DOMPurify) are each pinned to an exact
version and carry Subresource Integrity (`integrity` plus
`crossorigin="anonymous"`). DOMPurify sanitizes what marked returns, so it cannot
protect against a compromised marked: before 0.10.2 marked was loaded as
`marked@14`, a floating range, with no SRI. `tests/test_supply_chain.py` fails
any external script in the generator output or the committed `docs/demo.html`
and `docs/self.html` that lacks an exact version or SRI, and any third-party
script on the hand-written documentation pages. Bumping a library means recomputing its hash
(`openssl dgst -sha384 -binary | openssl base64 -A`) and running `make docs`.

# Layout

The page is a three-column grid: graph area, a drag handle, detail panel. The
title, controls and legend are overlays inside the graph area, so they never
cover the panel. The panel width is a `--side-w` custom property set by dragging
the handle (each side keeps at least 240px), reset by double-clicking it, and
remembered in `localStorage`. After a drag ends or the window resizes, the graph
re-runs the selected layout; it does not re-run during the drag.

# Derived signals

The panel infers rather than displays, because v0.3 defines these as derivations
and storing them would be storing an opinion:

* the **trust tier** (§5.3): no current `verified` is *unverified*, `verified` by
  non-`human:` actors only is *machine-confirmed*, any `human:` actor makes it
  *human-reviewed*. Only events at or after `generated.at` count, so a rewrite
  resets the tier and older confirmations stay as history;
* **staleness** (§5.5): *fresh*, *stale* or *malformed*. Python validates
  `stale_after` and hands the page a normalized UTC instant (or *malformed*,
  which is never fresh), and the page compares it with the clock when it is
  viewed, so a published `viz.html` turns stale on time instead of freezing
  the verdict of the day it was rendered.

Parsing follows the same written rule set as the
[MCP server](/components/mcp-server.md) and the
[validator](/components/validator.md), checked by
`tests/test_conformance_parity.py`. Frontmatter values are never stringified as
containers, so a YAML alias bomb renders as a placeholder instead of hanging
the build.

Both are advisory badges, not access control: nothing is hidden or refused on
their account.

# Flags

| Flag | Effect |
|------|--------|
| `--title` / `--link` | Name the graph; show a back-link to source. |
| `--layout` | Initial layout (`cose`, `breadthfirst`, `circle`, …); defaults to `cose` up to 1,000 concepts, then `concentric`. |
| `--og-image` | Emit Open Graph / Twitter Card meta for rich link previews. |
| `--max-nodes` | Refuse a bundle above N concepts (non-zero exit), for CI. |

Also supports `?layout=` / `?select=` URL params and deep-linkable concepts
(`viz.html#services/auth-api`).
