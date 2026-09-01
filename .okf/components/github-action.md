---
type: Tool
title: action.yml
description: Composite GitHub Action that runs the OKF validator against a bundle in any repo's CI, no Claude Code needed.
resource: https://github.com/scaccogatto/okf-skills/blob/main/action.yml
tags: [ci, github-actions, validator]
status: stable
generated: { by: agent:claude-opus-5, at: "2026-09-01T00:00:00Z" }
---

# Overview

The [dual-distribution decision](/decisions/dual-distribution.md) ships the
same validator as a third surface, for repos with no agent at all: a composite
GitHub Action wrapping the [validator](/components/validator.md)
(`okf_validate.py`). A consuming workflow references this repo's action in a
`uses:` step, without pinning a specific version here.

Marketplace constraints shape the manifest: `name` (`OKF Bundle Validator`)
must be globally unique among actions, users, and orgs, and `description`
must stay under 125 characters.

# Inputs

| Input | Default | Meaning |
|---|---|---|
| `bundle` | `.okf` | Path to the bundle directory. |
| `strict` | `"false"` | Treat every warning as an error (equivalent to `max-warnings 0`). |
| `max-warnings` | `""` | Fail if warnings exceed this count. Empty allows any number; errors still fail the run. |

# Outputs

`report`: the JSON report, as emitted by `okf_validate.py --json`, exposed via
`${{ steps.<id>.outputs.report }}` for a later step to post or parse.

# What the composite step does

One `runs: using: composite` job with two steps: `astral-sh/setup-uv@v5`, then
a single `bash` step (id `validate`). Inputs travel into the script through
`env` rather than being interpolated directly into the `run:` body, because a
bundle path is caller-controlled and `${{ }}` inside `run:` is textual
substitution, so a crafted value would execute as shell.

The script resolves `okf_validate.py` at
`$GITHUB_ACTION_PATH/skills/validate/scripts/okf_validate.py`, builds an
argument list (adding `--strict` when `strict` is `"true"`, `--max-warnings`
when `max-warnings` is non-empty), then runs it twice: once for the real exit
status, captured with `|| status=$?` (the default shell is `bash -e`, so a
plain `&&`/`[` test that evaluates false would otherwise abort the step), and
once more with `--json` to populate the `report` output via the
`GITHUB_OUTPUT` heredoc convention. The step exits with the captured
`status`, which is how failure is signalled: a non-conformant or
over-warning bundle makes the step (and the job) fail, exactly as a direct
`okf_validate.py` invocation would.

# Relationships

Exercised by the [ci.yml `action` job](/components/ci-workflow.md), which runs
it against this repo's own bundle with `strict: "true"` and again against
`tests/fixtures/non-conformant` to assert the failure path actually fails.
Wraps the same [validator](/components/validator.md) used directly by the
[validate skill](/skills/validate.md); shipping it is the third leg of the
[dual-distribution decision](/decisions/dual-distribution.md).
