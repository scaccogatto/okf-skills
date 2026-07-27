---
type: Tool
title: okf_validate.py
description: Zero-config Python conformance checker and v0.1→v0.2 migrator (PEP 723 / uv, PyYAML).
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/validate/scripts/okf_validate.py
tags: [python, validator, uv]
status: stable
generated: { by: human:scaccogatto, at: "2026-07-27T00:00:00Z" }
---

# Overview

The deterministic engine behind the [validate skill](/skills/validate.md). A
single self-describing script (dependencies declared inline via PEP 723) that
parses every non-reserved `.md` file and enforces the one hard rule of the
[OKF v0.2 spec](/reference/okf-spec.md): parseable YAML frontmatter with a
non-empty `type`.

# Checks beyond the hard rule

All soft, all warnings: `generated.by` present when `generated` is; every
`verified` entry has an actor (a bare mapping counts as a one-element list);
`status` is one of draft/stable/deprecated; `stale_after` and
`sources[].last_modified` are absolute `YYYY-MM-DD` dates; `generated.at` and
`verified[].at` are RFC 3339 (date-only tolerated); every `sources` entry has a
`resource`; a `usage_count` is framed by a `usage_window`; every `[^label]`
footnote names a `sources[].id`; an `Attested Computation` declares a `runtime`
and its path-valued `computation` / `executor.resource` / `attester.resource`
resolve inside the bundle. Legacy `timestamp` and `# Citations` warn with their
v0.2 replacement, per the [dual-read decision](/decisions/okf-v02-dual-read.md).

# The actor check (§7)

Deliberately not a whitelist — the spec's own §5.1 example uses
`author: team:ga4-docs`, so the `<prefix>:<id>` family is open. What is caught is
the one failure that is silent: a near-miss of `human:`. `Human:dana` satisfies
the generic shape and looks well-formed, while §5.3 keys trust tiers off that
exact lowercase prefix and reads it as an agent. `humanoid_agent/v1` is not a
near-miss and passes.

# Migration (`--migrate`)

The only mode that writes. Rewrites v0.1 constructs in place — `timestamp` to
`generated: { by: process:okf-migrate, at }`, a `# Citations` list up into
`sources`, `okf_version` to 0.2 — then validates. The rewrite is **textual**: a
PyYAML round-trip would flatten comments, key order and quoting across the whole
bundle. Each branch is guarded on the v0.2 key already existing, so a
half-migrated bundle converges instead of growing a duplicate key. See the
[migration decision](/decisions/okf-v02-dual-read.md) for what is deliberately
not recovered.

# Output

| Signal | Meaning |
|--------|---------|
| `ERROR` | Hard §11 failure — bundle is non-conformant. |
| `warn`  | Soft guidance (missing recommended field, broken link, legacy v0.1 field). |

Exit code is non-zero on any error, or when warnings exceed the gate: `--strict`
allows none, `--max-warnings N` allows N, the default allows any. `--json` emits
machine-readable output for CI.
