---
type: Tool
title: okf_validate.py
description: Zero-config Python v0.3 conformance checker and v0.1/v0.2→v0.3 migrator (PEP 723 / uv, PyYAML).
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/validate/scripts/okf_validate.py
tags: [python, validator, uv]
status: stable
generated: { by: "claude/opus-5.5", at: "2026-11-26T00:00:00Z" }
---

# Overview

The deterministic engine behind the [validate skill](/skills/validate.md). A
single self-describing script (dependencies declared inline via PEP 723) that
parses every non-reserved `.md` file and enforces the hard rules of
[OKF v0.3 §11.1](/reference/okf-spec.md): every frontmatter block parses as a YAML
mapping (a duplicate key is an error, and so is a broken root `index.md`
frontmatter).

A `.md` file without frontmatter or without a `type` is not a concept (§3.2), so
it is skipped with a **warning**, not an error. That is how a `README.md` or an
`AGENTS.md` can share the bundle directory. Dot-paths (`.git`, `.github`) are
skipped entirely.

# Checks beyond the hard rule

All soft, all warnings: `generated.by` present when `generated` is, and every
`verified` entry has both `by` and `at` (a bare mapping counts as a one-element
list). `status` is one of draft/stable/deprecated, and `superseded_by` resolves.
Timestamps (`generated.at`, `verified[].at`, `stale_after`,
`sources[].last_modified`, `usage_window`) are a date-only value or an RFC 3339
date-time with an offset and seconds. A date-time without an offset is invalid.
Every `sources` entry has a `resource`, and a `usage_count` is framed by a
`usage_window`. Every `[^label]` footnote names a `sources[].id` (code spans and
fenced blocks are skipped, as CommonMark does, so a regex class like `[^a-z]` in
code is not a footnote). An `Attested Computation` declares a `runtime`, its
`parameters` entries carry `name` and `type`, and its path-valued `computation`,
`executor.resource` and `attester.resource` resolve.

Path fields follow §6: a value without a leading `/` resolves from its file's
directory. A bundle declaring `okf_version` 0.2 or none also gets the §12.1 root
fallback, so a legacy bundle is not flooded with warnings. External targets
(a URI scheme) and targets outside the bundle root are not bundle paths.

The root `index.md` frontmatter is checked against the §8.1 keys (`okf_version`,
`title`, `description`, `license`), `x-` extension keys, and the plugin's own
`upkeep` and `recursive` (the Stop hook's flags, so an enforced-upkeep bundle
passes its own `--strict` run). `okf_version` must be quoted and match the
checked version. Legacy `timestamp` and `# Citations` warn with their
replacement, per the [dual-read decision](/decisions/okf-v02-dual-read.md).

# The actor check (§7)

Deliberately not a whitelist — the spec's own §5.1 example uses
`author: team:ga4-docs`, so the `<prefix>:<id>` family is open. What is caught is
the one failure that is silent: a near-miss of `human:`. `Human:dana` satisfies
the generic shape and looks well-formed, while §5.3 keys trust tiers off that
exact lowercase prefix and reads it as an agent. `humanoid_agent/v1` is not a
near-miss and passes.

# Migration (`--migrate`)

The only mode that writes. Rewrites v0.1 and v0.2 constructs in place to v0.3: a
`timestamp` becomes `generated: { by: process:okf-migrate, at }`, a `# Citations`
list moves up into `sources`, `okf_version` is bumped to 0.3, and block-style
path fields that were root-relative under §12.1 get a `/` prefix (root-only, so
nothing that already resolved from its own directory is touched). It then
validates. The rewrite is **textual**: a PyYAML round-trip would flatten
comments, key order and quoting across the whole bundle. Each branch is guarded
on the newer key already existing, so a half-migrated bundle converges instead of
growing a duplicate key. See the
[migration decision](/decisions/okf-v02-dual-read.md) for what is deliberately
not recovered.

# Output

| Signal | Meaning |
|--------|---------|
| `ERROR` | Hard §11.1 failure, the bundle is non-conformant. |
| `warn`  | Soft guidance (missing recommended field, broken link, legacy field, skipped non-concept). |

Exit code is non-zero on any error, or when warnings exceed the gate: `--strict`
allows none, `--max-warnings N` allows N, the default allows any. `--json` emits
machine-readable output for CI.
