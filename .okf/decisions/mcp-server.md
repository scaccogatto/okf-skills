---
type: Decision
title: Ship a read-only MCP server, for parity and not for capability
description: The July 2026 no-MCP call, re-read against a category that converged on one, then reversed on positioning with the original argument left intact.
tags: [adr, ecosystem, mcp]
status: stable
generated: { by: "agent:claude-opus-5", at: "2026-09-01T00:00:00Z" }
sources:
  - resource: https://github.com/scaccogatto/okf-skills/issues/41
    note: the re-read that reopened the question
  - resource: https://github.com/scaccogatto/okf-skills/issues/7
    note: the July 2026 competitive map, where the original decision lives
---

# Context

In July 2026 the competitive map in issue #7 declined an MCP server, and said so
out loud rather than leaving it as a gap:

> Claude Code already reads the filesystem; `search_concepts` / `read_concept` /
> `get_neighbors` would reimplement Grep and Read behind an extra process. It
> serves people whose agent *cannot* reach files, which is not who this is for.

That argument is about the **audience**, not about the competitor count. It is
still correct: this is a Claude Code plugin, and Claude Code has file tools.

Issue #41 re-read it against what moved since. Three toolkits added an MCP
server within a month:

| Tool | Verified | Note |
|---|---|---|
| `iwe-org/iwe` | yes (1.608★, `crates/iwe/src/init/okf.rs`) | *"CLI + MCP memory for your AI agents"* in the first line of its description; generates OKF |
| Kiso | no (author's post only) | closest in shape: a toolkit over the bundle, like this one |
| `openknowledge` | no (handles do not map to a GitHub account) | moved into the agent-memory category, where MCP is the default interface |

None of that touches the audience clause, and none of it is a user need. The
falsifying cases would be a bundle the agent has no checkout of, a team bundle
fronted by a service, or a host with no file tools at all. The first is the only
one inside this project's perimeter, and it does not come up in practice
(`git clone` answers it).

# Decision

Ship the server anyway, for **positioning**: absence from a category surface that
three peers now occupy costs more than the code does. Recorded as such rather
than dressed up as a capability gap.

Scope is the minimum that buys parity:

* `servers/okf_mcp.py`, read-only, stdio, PEP 723 so `uv run` resolves its deps.
* The three tools #7 named, under the names #7 named them:
  `search_concepts`, `read_concept`, `get_neighbors`.
* Wired into the plugin by `.mcp.json` at the plugin root; bundle from `$OKF_BUNDLE`,
  a CLI argument, or `./.okf`.
* A missing bundle is a readable tool error, not a startup failure: the plugin
  installs into projects that have no bundle yet.

# Consequences

* For Claude Code the server is redundant with Read and Grep, by construction.
  That is accepted, not solved. `/okf:okf` consume mode stays the recommended path.
* One more dependency (`mcp>=2`) and one more surface to keep alive across SDK
  churn. The SDK renamed `FastMCP` to `MCPServer` in 2.0; the tests dispatch through
  the SDK's own machinery so the next rename fails in CI and not at connect time.
* If the remote-bundle case ever becomes real, this is already the shape it needs.
* The July argument is **not** retired. If parity stops being worth a dependency,
  the server can go and the reasoning above still stands on its own.
