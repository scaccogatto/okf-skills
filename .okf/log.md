# Update Log

## 2026-07-27
* **Update**: Moved the toolkit to [OKF v0.2](/reference/okf-spec.md) — the
  [validator](/components/validator.md) checks the trust, lifecycle, provenance
  and attestation families, the [visualizer](/components/visualizer.md) renders
  them and draws `sources` edges, and [`okf_init.py`](/components/okf_init.md)
  scaffolds v0.2 frontmatter.
* **Decision**: Recorded [target v0.2, migrate v0.1 rather than tolerate
  it](/decisions/okf-v02-dual-read.md) — the legacy read branches buy warning
  wording, not compatibility, so the upgrade path is `--migrate`, not tolerance.
* **Update**: [`okf_validate.py`](/components/validator.md) gained `--migrate`
  (textual v0.1→v0.2 rewrite, idempotent) and `--max-warnings N` between the
  permissive default and `--strict`.
* **Migration**: This bundle moved to v0.2 — `timestamp` became
  `generated: {by, at}`, `# Citations` became `sources`, every concept gained
  `status`.
* **Build**: `make docs` now pins the exact invocation behind the two GitHub
  Pages demos, and CI fails on a stale `docs/`. They had drifted far enough to
  serve a build predating the DOMPurify sanitize fix — a security fix that
  reached the generator but never the pages it was for.
* **Trim**: Dropped the sample bundle's `Attested Computation` demo and the
  executor/attester it pointed at — a demo of a spec feature the toolkit
  implements nowhere.

## 2026-07-17
* **Update**: Added `okf_init.py` — scaffolds a conformant starter bundle
  (`index.md`, `log.md`, a full-frontmatter starter concept). Documented in
  the [okf skill](/skills/okf.md); CI asserts the scaffold passes
  `okf_validate.py --strict` with zero warnings.

## 2026-07-14
* **Scale guardrails**: the [visualizer](/components/visualizer.md) now defaults
  large bundles to a linear layout, warns past 5k concepts, batches/debounces
  filtering, and gains `--max-nodes` — see the
  [scale guardrails decision](/decisions/scale-guardrails.md).

## 2026-06-28
* **Creation**: Documented okf-skills in its own format — the three
  [skills](/skills/okf.md), the [validator](/components/validator.md) and
  [visualizer](/components/visualizer.md) components, the
  [vendored spec](/reference/okf-spec.md), and the architectural decisions
  ([dual distribution](/decisions/dual-distribution.md),
  [no hooks](/decisions/no-hooks.md),
  [self-contained skills](/decisions/self-contained-skills.md)).
