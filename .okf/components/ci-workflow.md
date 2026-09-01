---
type: Tool
title: ci.yml
description: GitHub Actions workflow that validates, exercises the action, and gates version bumps on every push and PR.
resource: https://github.com/scaccogatto/okf-skills/blob/main/.github/workflows/ci.yml
tags: [ci, github-actions, validation]
status: stable
generated: { by: agent:claude-opus-5, at: "2026-09-01T00:00:00Z" }
---

# Overview

Runs on push to `main` and on every pull request. `permissions: contents: read`
at the workflow level, since every job only reads the checkout. Four jobs:
`validate`, `action`, `validate-windows`, and `version-bump`.

# The `validate` job

Runs on `ubuntu-latest` with `astral-sh/setup-uv`. Steps, in order:

1. `jq empty` on `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
2. Unit tests for `okf_validate.py` internals.
3. Validates `examples/sample-bundle` and this repo's own `.okf` bundle, both
   `--strict` (the latter is the dogfooding check this bundle itself must pass).
4. Self-tests: success output survives a simulated cp1252 console, a
   non-conformant bundle is rejected, a v0.1 bundle reads by default, fails
   `--strict`, and `--migrate` clears it idempotently, `--max-warnings` gates
   between the default and `--strict`, the `okf_init.py` scaffold is
   strict-clean, script-breaking sequences in concept bodies do not corrupt
   `viz.html`, concept-body markdown is sanitized before `innerHTML`
   (DOMPurify, see the [visualizer](/components/visualizer.md)), and the
   scale guardrails (auto linear layout, `--max-nodes`) behave, per the
   [scale-guardrails decision](/decisions/scale-guardrails.md).
5. `make docs` and `git diff --exit-code -- docs/`: the committed GitHub Pages
   demos must match what the generator produces, so a fix like the DOMPurify
   sanitize change cannot land in the generator without also landing in the
   published pages.

# The `action` job

Exercises the composite [GitHub Action](/decisions/dual-distribution.md)
(`action.yml`) rather than assuming it works: runs it against this repo's own
`.okf` bundle (`strict: "true"`), then against `tests/fixtures/non-conformant`
with `continue-on-error: true` and asserts the step's outcome is `failure`.
Without the failing case a broken action would look green by never failing.

# The `validate-windows` job

Runs on `windows-latest`: real regression coverage for the cp1252 class of bug
(a genuine Windows console, not a simulated codepage on Linux) that originally
crashed the checker's ✓/✗/— glyphs. Runs the unit tests and a strict validate
of `examples/sample-bundle`.

# The `version-bump` job

Gates the [auto-release decision](/decisions/auto-release.md): a PR touching
the shipped surface must bump `.claude-plugin/plugin.json`'s version. Always
runs (no job-level `if`), so it can be a required status check without a
skipped run wedging it; the non-PR and `skip-version-check`-label cases exit 0
inside each step instead. Three steps:

1. **Require a version bump for shipped changes.** Shipped paths:
   `.claude-plugin/`, `skills/`, `hooks/`, `templates/`, `action.yml`. Compares
   `plugin.json`'s version at `BASE` and `HEAD`; passes only if `HEAD`'s is
   strictly higher.
2. **Require a changelog entry for the new version.** If the version changed,
   `CHANGELOG.md` must contain a `## [<version>]` heading.
3. **Require an `.okf/` update when a skill script changes.** If a path under
   `skills/*/scripts/` or `hooks/` changed, something under `.okf/` must have
   changed too.

Steps 2 and 3 mirror, on every PR, the same two obligations the plugin's Stop
hook enforces locally for anyone running it (see the [stop-hook
component](/components/stop-hook.md)); contributors not running the plugin
still hit the gate here. All three steps share the same PR-only guard and the
same `skip-version-check` label bypass.

# Relationships

Gates the [release workflow](/components/release-workflow.md) (which only
fires once the version is bumped), exercises the [action](/decisions/dual-distribution.md),
and enforces the [auto-release decision](/decisions/auto-release.md).
