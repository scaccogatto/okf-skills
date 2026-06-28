---
type: Tool
title: okf_validate.py
description: Zero-config Python conformance checker (PEP 723 / uv, PyYAML).
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/validate/scripts/okf_validate.py
tags: [python, validator, uv]
timestamp: "2026-06-28T00:00:00Z"
---

# Overview

The deterministic engine behind the [validate skill](/skills/validate.md). A
single self-describing script (dependencies declared inline via PEP 723) that
parses every non-reserved `.md` file and enforces the one hard rule of the
[OKF v0.1 spec](/reference/okf-spec.md): parseable YAML frontmatter with a
non-empty `type`.

# Output

| Signal | Meaning |
|--------|---------|
| `ERROR` | Hard §9 failure — bundle is non-conformant. |
| `warn`  | Soft guidance (missing recommended field, broken link). |

Exit code is non-zero on any error (or any warning with `--strict`). `--json`
emits machine-readable output for CI.
