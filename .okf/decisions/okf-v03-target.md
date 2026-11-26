---
type: Decision
title: Target OKF v0.3, read older bundles, migrate on request
description: Author v0.3 everywhere, read v0.1 and v0.2 with the spec's fallbacks, and rewrite on request with a verified migration.
tags: [adr, spec, compatibility, migration]
status: stable
generated: { by: "claude/opus-5.5", at: "2026-11-26T00:00:00Z" }
sources:
  - resource: https://github.com/open-knowledge-format/open-knowledge-format
    title: Open Knowledge Format specification
    author: team:open-knowledge-format
---

# Context

The spec moved to its own organisation and released v0.3 on 2026-11-18, with two
breaking changes. Path fields now resolve from the directory of the file that
holds them (v0.2 resolved from the bundle root), and trust tiers are derived
from current events only. Bundles authored against v0.1 and v0.2 exist, including
in repositories this toolkit does not control. This supersedes the
[v0.2 decision](/decisions/okf-v02-dual-read.md), whose policy it keeps.

# Decision

* Author v0.3 everywhere: [`okf_init.py`](/components/okf_init.md), the
  [okf skill](/skills/okf.md) templates and this repo's own bundle.
* Read v0.1 and v0.2 bundles with the §12.1 fallbacks and Appendix B. A legacy
  construct is a warning that names its replacement, never an error.
* `--migrate` rewrites older bundles to v0.3 textually, then verifies each rewrite
  by re-parsing and refuses any change beyond the intended `/` prefixes.
* The plugin's own root keys move to `x-okf-skills-upkeep` and
  `x-okf-skills-recursive`, because §4.1 reserves unprefixed keys for the spec.
  The old names stay as deprecated aliases: the Stop hook still reads them, the
  validator warns, and `--migrate` renames them.
* Plugin conventions are labelled as okf-skills conventions, not spec: the
  preference for `/`-rooted paths, a lifecycle-only `log.md`, and the
  recommended-field lint (`okf-skills lint`).
* The [validator](/components/validator.md), the
  [MCP server](/components/mcp-server.md) and the
  [visualizer](/components/visualizer.md) share one written rule set, enforced by
  `tests/test_conformance_parity.py`.

# Consequences

* An older bundle keeps working on day one, and `--migrate` is a single command
  away from being strict-clean.
* `--strict` still fails an unmigrated bundle. That stays the nudge, now with a
  verified door.
* A bundle that declares 0.2 and has root-only path fields keeps its old version
  until those fields are fixed, since bumping it would change what they mean.
* Three tools reading one rule set removes drift between them, at the cost of a
  parity test to maintain when the rules change.
* `generated.by` and per-claim attribution cannot be recovered for v0.1 content,
  as before.
