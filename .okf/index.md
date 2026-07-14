---
okf_version: "0.1"
---

# okf-skills — documented in its own format

This is the [okf-skills](https://github.com/scaccogatto/okf-skills) repository
described as an OKF bundle — the toolkit eating its own dog food. Render it with
`/okf:visualize .okf` (or see the [live graph](https://scaccogatto.github.io/okf-skills/self.html)).

# Skills

* [okf skill](skills/okf.md) — produce / maintain / consume bundles.
* [validate skill](skills/validate.md) — deterministic §9 conformance check.
* [visualize skill](skills/visualize.md) — render a bundle to an interactive graph.

# Components

* [okf_validate.py](components/validator.md) — the conformance checker.
* [okf_visualize.py](components/visualizer.md) — the graph renderer.

# Reference

* [OKF v0.1 specification](reference/okf-spec.md) — the vendored source of truth.

# Decisions

* [Dual distribution — plugin + skills.sh](decisions/dual-distribution.md)
* [Ship no hooks — soft-mode upkeep](decisions/no-hooks.md)
* [Self-contained skills via CLAUDE_SKILL_DIR](decisions/self-contained-skills.md)
* [Scale guardrails in the visualizer](decisions/scale-guardrails.md)
