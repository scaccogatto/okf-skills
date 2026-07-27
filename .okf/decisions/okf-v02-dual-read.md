---
type: Decision
title: Target OKF v0.2, migrate v0.1 rather than tolerate it
description: Author v0.2 everywhere; name the legacy constructs in warnings and ship the rewrite that clears them.
tags: [adr, spec, compatibility, migration]
status: stable
generated: { by: human:scaccogatto, at: "2026-07-27T00:00:00Z" }
---

# Context

[OKF v0.2](/reference/okf-spec.md) supersedes v0.1 with two breaking renames —
`timestamp` becomes `generated.at`, and the body `# Citations` list becomes the
`sources` frontmatter family (§13.1). Bundles authored against v0.1 exist,
including in repositories this toolkit does not control.

Compatibility, however, was never at risk. §11 has two hard rules — parseable
YAML frontmatter and a non-empty `type` — and neither mentions `timestamp` or
`# Citations`. A v0.1 bundle is conformant under v0.2 **with no code on our
side**: same `conformant: true`, same warning count, same `--strict` outcome.
What dedicated legacy branches buy is the wording of one warning, nothing more.

That reframes the real question. The upgrade hazard is not reading v0.1, it is
that [`templates/CLAUDE-okf.md`](/skills/okf.md) tells every user to run
`--strict` before committing. Left alone, everyone holding a v0.1 bundle hits a
hard failure on their next commit with no way out but a hand edit.

# Decision

Keep the legacy branches for their wording, and **ship the rewrite that clears
them**.

* The [validator](/components/validator.md) reports a legacy `timestamp` or a
  `# Citations` section as a **warning naming its v0.2 replacement** — never an
  error. Eleven lines, kept because a warning that names the fix is worth more
  than one that says a field is missing.
* The [visualizer](/components/visualizer.md) falls back to `timestamp` when
  `generated` is absent, so a v0.1 bundle still shows a date.
* `--migrate` performs the rewrite textually — never a PyYAML round-trip, which
  would flatten comments, key order and quoting across the whole bundle.
* Everything that *writes* — [`okf_init.py`](/components/okf_init.md), the
  [okf skill](/skills/okf.md)'s templates, and this repo's own bundles — emits
  v0.2 only.

# Consequences

* An existing v0.1 bundle keeps working on day one, and `--migrate` is a single
  command away from being strict-clean.
* `--strict` still fails an unmigrated v0.1 bundle. That stays the nudge — it is
  now a nudge with a door, not a wall.
* `generated.by` cannot be reconstructed for content written before the field
  existed. The migration writes `process:okf-migrate`, which is true and leaves
  the concept correctly **unverified** under §5.3 rather than faking review.
* Per-claim attribution (the `[^id]` footnotes of §5.1) is not recoverable from
  a v0.1 `# Citations` list: the sources move up to frontmatter, but which claim
  cited which source was never encoded. `--migrate` says so instead of guessing.
