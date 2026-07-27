---
type: Decision
title: Target OKF v0.2, keep reading v0.1
description: Author v0.2 everywhere; accept v0.1 bundles with a warning instead of an error.
tags: [adr, spec, compatibility]
status: stable
generated: { by: human:scaccogatto, at: "2026-07-27T00:00:00Z" }
---

# Context

[OKF v0.2](/reference/okf-spec.md) supersedes v0.1 with two breaking renames —
`timestamp` becomes `generated.at`, and the body `# Citations` list becomes the
`sources` frontmatter family (§13.1). Bundles authored against v0.1 already
exist, including in repositories this toolkit does not control. The spec itself
tells consumers to fall back rather than refuse.

# Decision

Read both, write v0.2.

* The [validator](/components/validator.md) reports a legacy `timestamp` or a
  `# Citations` section as a **warning** naming its v0.2 replacement — never an
  error. §11 conformance is unchanged: parseable frontmatter with a non-empty
  `type`.
* The [visualizer](/components/visualizer.md) falls back to `timestamp` when
  `generated` is absent, so a v0.1 bundle still shows a date.
* Everything that *writes* — [`okf_init.py`](/components/okf_init.md), the
  [okf skill](/skills/okf.md)'s templates, and this repo's own bundles — emits
  v0.2 only.

No migration script ships. The [okf skill](/skills/okf.md) knows the rewrite, and
the validator's warnings point at every file that needs it.

# Consequences

* An existing v0.1 bundle keeps working on day one; nothing breaks on upgrade.
* `--strict` does fail a v0.1 bundle, since the legacy warnings are warnings.
  That is the intended nudge, not an accident.
* The legacy branches are two `if`s in the validator and one in the visualizer —
  cheap enough to keep until v0.1 bundles are gone.
