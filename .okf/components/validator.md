---
type: Tool
title: okf_validate.py
description: Zero-config Python conformance checker (PEP 723 / uv, PyYAML).
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
`sources[].last_modified` are absolute `YYYY-MM-DD` dates; every `sources` entry
has a `resource`; every `[^label]` footnote names a `sources[].id`; an
`Attested Computation` declares a `runtime`. Legacy `timestamp` and
`# Citations` warn with their v0.2 replacement, per the
[dual-read decision](/decisions/okf-v02-dual-read.md).

# Output

| Signal | Meaning |
|--------|---------|
| `ERROR` | Hard §11 failure — bundle is non-conformant. |
| `warn`  | Soft guidance (missing recommended field, broken link, legacy v0.1 field). |

Exit code is non-zero on any error (or any warning with `--strict`). `--json`
emits machine-readable output for CI.
