---
okf_version: "0.2"
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

* [okf_init.py](components/okf_init.md) — the starter bundle scaffolder.
* [okf_validate.py](components/validator.md) — the conformance checker.
* [okf_visualize.py](components/visualizer.md) — the graph renderer.

# Reference

* [OKF v0.2 specification](reference/okf-spec.md) — the vendored source of truth.

# Decisions

* [Dual distribution — plugin + skills.sh](decisions/dual-distribution.md)
* [Ship no hooks — soft-mode upkeep](decisions/no-hooks.md)
* [Self-contained skills via CLAUDE_SKILL_DIR](decisions/self-contained-skills.md)
* [Scale guardrails in the visualizer](decisions/scale-guardrails.md)
* [Target OKF v0.2, keep reading v0.1](decisions/okf-v02-dual-read.md)
