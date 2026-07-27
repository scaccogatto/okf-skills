# Update Log

## 2026-07-27
* **Measurement**: Ran the first benchmark of whether a bundle helps an agent —
  12 fresh agents, this repo with and without `.okf/`, blind grading. Result:
  +8 points of claim coverage, **no token saving** (the bundle arm cost 5% more,
  which at n=1 is noise). The bundle won the *why* questions and lost the
  *where-do-I-change-this* one. Recorded in `benchmark/`, and the README's
  progressive-disclosure claim is now qualified by it.
* **Update**: The [visualizer](/components/visualizer.md) now *derives* the §5.3
  trust tier and staleness instead of printing raw dates — the inference v0.2 is
  named for. Both computed at render time; OKF stores neither on purpose.
* **Update**: The [validator](/components/validator.md) gained the §7 actor check
  (aimed at near-misses of `human:`, the one actor typo that silently changes a
  trust tier), `usage_window`, RFC 3339 instants, and resolution of the
  Attested Computation path-valued fields.
* **Distribution**: Added a composite GitHub Action so a bundle can be gated in
  any repo's CI without Claude Code. CI exercises both its passing and failing
  path — an action that never fails would look green for the wrong reason.
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
