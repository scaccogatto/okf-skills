# Update Log

## 2026-09-01
* **Fix**: [backfill](/skills/backfill.md) `repo_slug()` now maps every
  non-alphanumeric character to a dash, matching Claude Code's real transcript
  dir naming (`p-045_ekar_skills` -> `p-045-ekar-skills`); underscores in the
  repo path previously yielded zero session events. Plugin 0.9.0 to 0.9.1.
* **Fix**: The [backfill](/skills/backfill.md) extractor and its tests are now
  Windows-portable: `repo_slug()` maps `\` and drive colons to dashes alongside
  `/` and `.`, the cwd filter compares `Path`s instead of string prefixes, and
  the tests use a real resolvable temp path plus a `__file__`-derived cwd
  instead of a hardcoded machine-local worktree path (which broke CI on both
  runners).
* **Trust benchmark, revision 4 and the first executable pieces**: the
  [protocol](/decisions/trust-benchmark.md) gained a harness, a grader, an
  analysis script and a frozen item format; still nothing has been run. The
  revision was forced by checking §8 against the API rather than against memory:
  `claude-opus-5` rejects `temperature` with a 400 and the Messages API has no
  seed parameter, so the section written specifically to remove placeholders had
  frozen two values that do not exist. `effort` and `thinking` are pinned in
  their place, and per-trial response ids replace the seeds §13 promised to
  publish.
* **Dogfooding**: Armed the [dormant Stop hook](/decisions/dormant-hooks.md) on
  this repo. `.okf/index.md` now carries `upkeep: enforced`, so the plugin's own
  hook blocks a session that changed tracked files without touching
  `.okf/log.md`. The bundle shipping the enforcement mechanism was the one repo
  not using it, relying instead on a maintainer's machine-level hook that no
  contributor has.
  Arming it surfaced a second defect: the [validator](/components/validator.md)
  warned `§12 root index.md frontmatter may only carry \`okf_version\``, so any
  enforced-mode bundle failed its own `--strict` run. `upkeep` is now allowed
  next to `okf_version`.
* **Documentation**: Full freshness audit of every human-facing surface (README,
  CHANGELOG, the three `SKILL.md` files, this bundle, `action.yml` and the
  workflows), each claim re-checked against the code it describes. 42 verified
  defects, of which five were wrong rather than merely stale: `--strict` was
  documented as never blocking on warnings while the commands shown beside it
  pass `--strict`; the visualizer's bundle argument was documented as optional
  and is required; nodes were documented as sized by type and are sized by body
  length; "no data leaves the page" omitted the three CDN libraries the rendered
  page loads. The changelog had drifted three releases behind `plugin.json`,
  which is what motivated the CI gate below. Two shipped assets turned out to
  have no concept at all and now do: [ci.yml](/components/ci-workflow.md) and
  [action.yml](/components/github-action.md).
* **Release**: The floating `v1` tag now follows every release
  ([release.yml](/components/release-workflow.md)). It had been created by hand
  on a docs commit and never moved, so the README's own action example ran a
  validator from 0.6.0, one that rejects the `upkeep` flag the README tells
  adopters to add. Pinning the README to an exact tag was the alternative and
  was rejected: it is another thing someone has to remember, which is precisely
  how this drifted.
* **Enforcement**: Mirrored the [Stop hook](/components/stop-hook.md)'s two
  obligations into CI, as steps on the existing `version-bump` job. A PR that
  touches `skills/*/scripts/**` or `hooks/**` must also touch `.okf/`, and a PR
  that bumps the version must add the matching `CHANGELOG.md` heading. The hook
  only reaches people running the plugin; a contributor on a plain checkout had
  no obligation at all, which is how the changelog drifted three releases behind
  `plugin.json` unnoticed.
* **Message**: The §11.1 error now names its fix. A third-party bundle shipping
  an `AGENTS.md` next to its concepts was told only "no parseable YAML
  frontmatter block", which is true and useless to someone who never meant that
  file as a concept. The [validator](/components/validator.md) now points at the
  two ways out (add a `type`, or move the file outside the bundle). Exempting
  convention filenames was rejected: §11.1 covers every non-reserved `.md` in the
  tree, so a skip-list would make the checker itself non-conformant (v0.7.3).
* **Bugfix**: The backfill skill's session-transcript extractor
  (`skills/backfill/scripts/okf_backfill_events.py`) was written against an
  invented transcript schema and its tests matched the bug instead of real
  files. Rewrote `sessions_from_transcripts` against the real envelope
  (`message.content`, `timestamp`, `gitBranch`, `aiTitle`), added the missing
  `cwd` filter, fixed outcome pairing to take the last assistant text block
  per turn, used real 1-based line numbers in event ids, fixed
  `truncate_text`'s bound and multi-`--branch` union/dedup, and switched
  output `ts` to ISO8601 UTC (`...Z`). Tests rewritten against the real
  schema; dogfooded on this repo: 148 events (44 git, 104 session),
  byte-identical across two runs.

* **MCP server**: added [`okf_mcp.py`](/components/mcp-server.md), a read-only
  stdio server over a bundle (`search_concepts`, `read_concept`, `get_neighbors`),
  wired into the plugin by `.mcp.json`. It reverses the July 2026 "no MCP" call on
  positioning grounds only; the original audience argument is intact and recorded
  in the [MCP server decision](/decisions/mcp-server.md). Plugin 0.7.4 to 0.8.0.
* **Skill**: Shipped the `backfill` skill, event-sourcing reconstruction of OKF
  bundles from git history and Claude session transcripts. Extracts events
  deterministically (same repo -> byte-identical events.jsonl); replays via LLM
  interpretation with drift-aware metadata. Designed for repos created before OKF
  adoption to capture their actual decision narrative. Includes a deterministic
  skip-rule classifier (lockfiles, merge-only commits, slash-command noise) and
  cursor-based resume-safe replay loop. Bumped version to 0.9.0.

## 2026-08-16
* **Benchmark returns, measuring something else**: `benchmark/trust/` adds a
  protocol for the one claim the spec leads with and nobody has tested —
  trustability. See [the decision](/decisions/trust-benchmark.md) for why this is
  not what #32 removed. Nothing has been run; the protocol was rejected twice in
  adversarial review (an underpowered criterion, a grader that broke on the most
  likely answer shape, a power analysis whose input did not exist in its own
  calibration data, and a metric undefined exactly where the treatment arm
  concentrates refusals) before being cleared as executable.

## 2026-08-15
* **Distribution**: Published the composite action to the GitHub Marketplace.
  The listing form rejected the shipped metadata — the name `Validate OKF
  bundle` was not globally unique and the description exceeded 125 characters —
  so `action.yml` now reads `OKF Bundle Validator` with a trimmed description
  (v0.7.2). Consumers reference `scaccogatto/okf-skills@<tag>` regardless, so
  the rename breaks nothing.

## 2026-08-03
* **Enforcement**: Made the version bump mandatory. A `version-bump` CI job fails
  any PR that changes the shipped surface (`.claude-plugin/`, `skills/`, `hooks/`,
  `templates/`, `action.yml`) without raising `plugin.json`'s version; docs/`.okf/`
  /tests are exempt and a `skip-version-check` label bypasses it. This closes the
  gap the [auto-release](/decisions/auto-release.md) trigger left: a release now
  can't be skipped by simply forgetting to bump.
* **Decision**: Automated releases. A [`release` workflow](/components/release-workflow.md)
  now tags and publishes `okf--v<version>` whenever a push to `main` changes
  `plugin.json`'s version — releasing was manual and got skipped (0.7.0 and 0.7.1
  were bumped but never released). Recorded in
  [auto-release](/decisions/auto-release.md); cut the missing v0.7.1 release by
  hand.
* **Removal**: Deleted the whole `benchmark/` tree (the with/without run, its
  reframes, and the unrun cross-session "repetition" protocol). Checked the
  canonical spec (Google `knowledge-catalog`, the vendored `SPEC.md`): OKF's
  stated intent (§1) is portable, diffable, *trustable* knowledge exchange — it
  makes no claim about tokens, cost, or answer quality (those words appear zero
  times). The benchmark measured the ecosystem's adoption pitch, not the
  standard, so it does not belong in the toolkit for the standard. Earlier log
  entries mentioning `benchmark/` are left as history.

## 2026-08-02
* **Fix**: [`okf-stop-check.sh`](/components/stop-hook.md) now counts only
  *modified tracked files*, not any untracked path — it false-fired on the
  first real-world trigger (an untracked `.claude/` worktree dir, in this very
  repo). Ignoring all untracked paths fixes the whole class (`.venv/`,
  `.DS_Store`, build dirs) instead of whitelisting one; a new untracked file
  is not yet a documented asset. Also gitignored `.claude/` here as hygiene.
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
