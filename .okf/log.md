# Update Log

## 2026-08-02
* **Decision**: Recorded [dormant hooks — opt-in enforced
  upkeep](/decisions/dormant-hooks.md) and shipped the plugin's first hook,
  [`okf-stop-check.sh`](/components/stop-hook.md) on `Stop` — a no-op unless a
  bundle sets `upkeep: enforced` in `.okf/index.md` and the user hasn't set
  `OKF_HOOK=off`. This supersedes [ship no hooks](/decisions/no-hooks.md),
  now `deprecated`.

## 2026-07-29
* **Reframe**: The benchmark docs now lead with what the experiment measured —
  answer quality, +8 points with a consistent why/where pattern — and scope the
  token result to what a one-question-per-session design can see, which excludes
  the cross-session repetition cost a bundle is adopted against. That experiment
  ("What to measure next" in `benchmark/results.md`) is specced and unrun; no
  token claim, favourable or not, until it runs. Prompted by
  [#21](https://github.com/scaccogatto/okf-skills/issues/21).
* **Review**: Re-read the vendored spec's §1 intents against the benchmark
  discourse. The tested claim — better answers, cheaper reading — is the
  ecosystem's adoption pitch; the spec stakes v0.2 on trust of agent-written
  corpora, which a pristine bundle never exercises. Added the trust-calibration
  experiment (seeded rot, flat-notes arm) to `benchmark/results.md`, scoped the
  README's selective-reading row to §8's actual promise, and named the tested
  claim's origin in `benchmark/README.md`.

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
