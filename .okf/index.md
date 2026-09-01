---
okf_version: "0.2"
upkeep: enforced
---

# okf-skills — documented in its own format

This is the [okf-skills](https://github.com/scaccogatto/okf-skills) repository
described as an OKF bundle — the toolkit eating its own dog food. Render it with
`/okf:visualize .okf` (or see the [live graph](https://scaccogatto.github.io/okf-skills/self.html)).

# Skills

* [okf skill](skills/okf.md) — produce / maintain / consume bundles.
* [validate skill](skills/validate.md) — deterministic §11 conformance check.
* [visualize skill](skills/visualize.md) — render a bundle to an interactive graph.

# Components

* [okf_init.py](components/okf_init.md): the starter bundle scaffolder.
* [okf_validate.py](components/validator.md): the conformance checker.
* [okf_visualize.py](components/visualizer.md): the graph renderer.
* [okf-stop-check.sh](components/stop-hook.md): the dormant Stop hook.
* [release.yml](components/release-workflow.md): auto-release on version bump.
* [ci.yml](components/ci-workflow.md): validate, action, Windows and version-bump jobs.
* [action.yml](components/github-action.md): composite GitHub Action wrapping the validator.

# Reference

* [OKF v0.2 specification](reference/okf-spec.md) — the vendored source of truth.

# Decisions

* [Dual distribution: plugin, skills.sh, GitHub Action](decisions/dual-distribution.md)
* [Ship no hooks: soft-mode upkeep](decisions/no-hooks.md): *deprecated*, superseded by dormant hooks.
* [Ship a dormant Stop hook: opt-in enforced upkeep](decisions/dormant-hooks.md)
* [Auto-release on version bump](decisions/auto-release.md)
* [Self-contained skills via CLAUDE_SKILL_DIR](decisions/self-contained-skills.md)
* [Scale guardrails in the visualizer](decisions/scale-guardrails.md)
* [Target OKF v0.2, migrate v0.1 rather than tolerate it](decisions/okf-v02-dual-read.md)
