---
type: Tool
title: okf_mcp.py
description: Read-only MCP server over a bundle — search_concepts, read_concept, get_neighbors.
resource: https://github.com/scaccogatto/okf-skills/blob/main/servers/okf_mcp.py
tags: [python, mcp, consumer]
status: stable
generated: { by: "agent:claude-opus-5", at: "2026-09-01T00:00:00Z" }
---

# Overview

A stdio MCP server exposing one OKF bundle read-only. Why it exists at all, given
that Claude Code reads files directly, is the
[MCP server decision](/decisions/mcp-server.md).

Wired into the plugin by `.mcp.json` at the repo root; standalone it is
`uv run servers/okf_mcp.py [bundle-dir]`. The bundle is the first argument, else
`$OKF_BUNDLE`, else `./.okf`. A missing bundle does not stop the server: it
surfaces as an error on the first tool call, so the plugin stays quiet in projects
that have no bundle.

# The tools

| Tool | Returns |
|---|---|
| `search_concepts(query, limit=20)` | Cards (`id`, `type`, `title`, `description`, `status`, `stale_after`) for concepts matching `query`, case-insensitively. Metadata hits (id, title, description, tags) rank above body-only hits. |
| `read_concept(concept_id)` | The file verbatim, frontmatter included. `concept_id` is the bundle-relative path without `.md`; the reserved `index` and `log` are reachable too. |
| `get_neighbors(concept_id)` | `outgoing` and `incoming` cards — markdown links plus bundle-internal `sources[].resource`, resolved with the same rule as the [visualizer](/components/visualizer.md). External URLs are not neighbours. |

Nothing writes, and no tool takes a path outside the bundle: `concept_id` is
resolved and rejected unless it lands under the bundle root.

# Notes

* Parsing is the `split_frontmatter` / `link_targets` / `resolve` trio shared in
  shape with the [visualizer](/components/visualizer.md), duplicated rather than
  imported to keep the server runnable on its own
  ([self-contained skills](/decisions/self-contained-skills.md)).
* The bundle is re-read on every call. Correct while a bundle is being edited,
  and cheap up to a few thousand concepts.
* `mcp>=2`: the SDK renamed `FastMCP` to `MCPServer` in 2.0. `tests/test_okf_mcp.py`
  dispatches through the SDK rather than calling the functions directly, so a
  further rename breaks CI instead of production.
