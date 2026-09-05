# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this plugin tracks the
OKF spec version it supports.

## [Unreleased]

### Added
- **Capped diff emitter for the backfill map phase.** `okf_backfill_events.py --show <sha>`
  reads the whole first-parent diff and emits a deterministic sample under the harness
  limits: complete stat, patches capped per file (default 300 lines total, 120 per file,
  400 chars per line) and cut at hunk or file boundaries with a marker at every cut,
  generated files' patches omitted even inside mixed commits, and a fixed last line
  declaring `truncated=true|false`. `--only <path>` is the one permitted follow-up.
  Analyzers never run a raw `git show` again; the harness cut long output blindly and
  a cheap worker could not tell. 14 unit tests, including merge commits and the
  accounting closure between shown, declared and total lines.
- **Map-phase routing benchmark** (`benchmark/map-tier/`): an engineering A/B of the
  analyzer tier (sonnet vs haiku) and dispatch shape (solo vs batched) on this repository's
  own 147-event history, with paired per-event deterministic metrics and decision rules
  written before the run. Batching small events eight per call cut the map phase by a third
  at the same tier with no measurable loss. The cheap tier extracted commits at parity and
  failed two contract rules in run 1; both traced to under-specified instructions, now
  explicit in the analyzer file, and were re-measured in runs 2 and 3. The reduce phase
  costs as much as a sonnet map in every configuration: the next lever is the weaver's
  context shape, not the analyzer tier.
- **Dispatch rule for the map phase.** A session turn or a commit of at most 60 changed
  lines is small; small events go eight per analyzer call, large commits alone. Deterministic
  from `events.jsonl`, documented with its `jq` one-liner in the skill.
- **Decision record** `.okf/decisions/map-phase-routing.md`: what was adopted from the
  Spotify routing pattern, what was deferred (hooks) and what diverges on purpose (analyses
  are kept for audit and resume).

### Changed
- **Backfill contracts.** The orchestrator dispatches event ids and reads counts only
  (never `events.jsonl`, analyses or diffs); analyzers fetch their own events with `jq`,
  write bullets-only analyses with a `truncated` flag, and reply one line per event;
  the weaver replies counts. Finalize reports agents per phase and truncated analyses.
- **Concurrency guidance.** Map-phase waves of 4 to 8 replace the "64 analyzers" claim,
  citing the gate benchmark's high-concurrency mass failure.
- **Analyzer default tier: `haiku`** (`agents/event-analyzer.md`), after run 3 of the
  map-tier benchmark passed every pre-set rule with two instructions made explicit (which
  emitter summary line the `truncated` flag copies; claims report intent as intent, never
  the plausible continuation). Against sonnet solo: parity or better on every per-event
  metric, the truncation flag at the threshold (0.905), map cost −43% solo and −62%
  batched. The file documents that its tier is configuration: fork it to retier.

## [0.9.3] — 2026-09-03

### Added
- **Two measured experiments, published with their own qualifications.**
  `benchmark/trust/` tests the claim the spec leads with: do the v0.2 lifecycle
  and trust fields stop a consumer asserting superseded facts? The channel
  works — with that frontmatter present the consumer never asserted a
  superseded fact across 473 trials, and it reads `status`, `stale_after` and
  `verified` without being told what they mean — but **the primary contrast is
  invalid under the protocol's own rule**, because too many items produced no
  committed answer in the control arm. `benchmark/gate/` tests whether a
  write-side process gate makes that metadata redundant: it does not, and the
  metadata does not make a gate pointless either. A gate cut stale answers by
  39pp, an expired `stale_after` by 28pp, and 20 items cannot tell the two
  apart. Both protocols were pre-registered and tagged before their measurement
  run; corpora, transcripts and every trial record are published, along with
  the defects the runs exposed.
- **A README section that leads with the qualification.** "What has actually
  been measured" points at both results files and states, before the numbers,
  that neither experiment estimates what OKF is worth in a real repository —
  where prose, filenames and history already carry recency.

### Changed
- **CI gates the benchmark suites.** The gate benchmark's tests run alongside
  the trust benchmark's, for the reason already stated there: the analysis is
  what decides whether a published comparison is honest. Its direction tests
  exist because the trust benchmark's analysis had its effect sign inverted and
  nothing exercised it until a real result arrived.

## [0.9.2] — 2026-09-01

### Added
- **Two dedicated agents for deep semantic replay:** `okf:event-analyzer` (map phase,
  parallel) reads each git commit diff or session turn to extract domain rationale and
  candidate concept names. `okf:bundle-weaver` (reduce phase, sequential) folds analyses
  into the bundle while enforcing anti-degeneration rules and managing cursor state.
  Together they replace the single-pass replay loop, enabling deep understanding of *why*
  changes were made (from diffs and session outcomes) instead of mechanical concept
  listing.

### Changed
- **Replay protocol is now two-phase (map/reduce).** Map phase is massively parallel
  (~64 analyzers per wave); reduce is sequential but much cheaper (analysis done, weaving
  is binding). Both phases support resume via cursor. See §2 of SKILL.md for orchestration
  details and fallback patterns for hosts without Workflow support.
- **Finalize now includes deterministic coverage check.** A new `--check-coverage`
  subcommand to the extractor verifies that every live event (no `skip` field) appears
  in the bundle's `sources` or log, exiting 1 if any are unmapped. This guarantee is
  constructive (the weaver proves coverage as it works) and auditable (the cursor tracks
  which events were processed).

### Added
- **Anti-degeneration rules with enforcement.** Concepts must be named for domain
  entities (`presales-pipeline.md`, not `feat:-add-presales-pipeline.md` or
  `merge-pull-request-#2.md`). Filenames must be kebab-case. Log bullets must explain
  intent, not restate subjects. No consecutive identical bullets. The analyzer and weaver
  are responsible for proposing and enforcing these; the finalize step validates via bash.

### Added
- **Cost transparency and Lore protocol support.** Documented the cost of deep replay
  (reads ~1 diff per commit; ~500-event sweet spot). Noted support for git trailers
  (Lore protocol) as primary source of "why" on repos that adopt structured metadata.

## [0.9.1] — 2026-09-01

### Fixed
- **`backfill` found zero session transcripts for repos with `_` (or any
  non-alphanumeric beyond `/ \ : .`) in their path.** `repo_slug()` now maps
  every non-alphanumeric character to a dash, matching how Claude Code names
  transcript directories.

## [0.9.0] — 2026-09-01

### Added
- **`backfill` skill reconstructs an OKF bundle from history.** Event-sources a
  repository's decision log (git commits + Claude session transcripts) to rebuild
  its `.okf/` bundle as if the stop hook had been active from the start. Extraction
  is deterministic (same repo → byte-identical events.jsonl); replay is an LLM loop
  (replayable and auditable, with drift-aware trust metadata). Designed for repos
  that predate this toolchain and want their OKF bundle to reflect the actual
  history of decisions.

## [0.8.0] - 2026-09-01

### Added
- **A read-only MCP server over a bundle** (`servers/okf_mcp.py`), wired into the
  plugin by `.mcp.json` and started with it. Three tools, the shape the rest of
  the OKF ecosystem converged on: `search_concepts`, `read_concept`,
  `get_neighbors`. Nothing writes, and no `concept_id` resolves outside the
  bundle root. The bundle comes from a CLI argument, `$OKF_BUNDLE`, or `./.okf`.

  For Claude Code this duplicates Read and Grep, which is why it was declined in
  July. It ships for parity with a category that now expects it, and
  [`.okf/decisions/mcp-server.md`](.okf/decisions/mcp-server.md) records that as
  the reason rather than inventing a capability gap. A project with no bundle
  still gets a connected server, and a readable error on the first call.

  The handshake reports the plugin version, read from `plugin.json` rather than
  restated in the server, so a release cannot leave the two disagreeing.

## [0.7.4] — 2026-09-01

### Changed
- This repo's own `.okf/` bundle now declares `upkeep: enforced`, arming the
  plugin's own Stop hook on this repo. The bundle that ships enforced upkeep
  was the one bundle not using it, so upkeep here rested on a maintainer's
  machine-level hook no contributor has, which is how CHANGELOG.md drifted
  three releases behind `plugin.json` without anyone noticing.

### Fixed
- **`validate` accepts `upkeep` in the root `index.md` frontmatter**, alongside
  `okf_version`. Without it, the §12 warning fired on the very key just
  described above, so every bundle opting into enforced upkeep failed its own
  `--strict` validation, this repo's included.

### Added
- CI: two new steps mirror the Stop hook's obligations onto pull requests, so
  a contributor sending a PR from a plain checkout gets the same nudge a local
  session gets. A version bump must add the matching `## [version]` heading to
  CHANGELOG.md, and a PR touching `skills/*/scripts/**` or `hooks/**` must also
  touch `.okf/`. Both steps live on the existing version-bump job rather than a
  new one, so the set of required status checks does not change, and both take
  that job's `skip-version-check` label as their bypass.

### Fixed
- **The floating `v1` tag follows every release.** It had been created by hand
  on a docs commit and never moved, so `uses: scaccogatto/okf-skills@v1`, the
  form the README shows, ran the validator from 0.6.0: the one that rejects the
  `upkeep` flag the README tells adopters to add, failing their CI on our
  instructions. `release.yml` now force-moves it onto each release commit. The
  repo is pre-1.0, so `v1` tracks the latest release rather than a major line,
  stated in the README beside the example. Pin `@okf--v<version>` to freeze.

### Docs
- **Every documented claim re-checked against the code it describes**, across
  the three shipped `SKILL.md` files. Five were wrong rather than stale:
  `--strict` was documented as never blocking on warnings, beside two commands
  that pass `--strict` (it exits 1 on any warning); the visualizer's bundle
  argument was documented as optional and is a required positional; nodes were
  documented as sized by type and are sized by body length; "no data leaves the
  page" omitted the three CDN libraries the rendered page loads at view time
  (bundle content does stay local, the viewer still needs network). `validate`
  now also lists the checks it had omitted (unreadable UTF-8, a missing
  `runtime`, frontmatter in a reserved file, §12), `okf` documents
  `usage_window`, and `visualize` gains a full flag table and the deep-link
  parameters. Two shipped assets had no concept in this repo's own bundle and
  now do: `ci.yml` and `action.yml`.

## [0.7.3] — 2026-09-01

### Fixed
- **The §11.1 frontmatter error now names the way out.** A bundle shipping a
  convention file next to its concepts (an `AGENTS.md` scoping agent rules to
  that directory) was told only "no parseable YAML frontmatter block", true and
  useless to someone who never meant that file as a concept. Exempting
  well-known filenames or downgrading to a warning was rejected, since §11.1
  covers every non-reserved `.md` in the tree and either would make the checker
  itself non-conformant. The message now states both fixes: add frontmatter with
  a `type`, or move the file outside the bundle (#42).

## [0.7.2] — 2026-08-15

### Changed
- **The action is now `OKF Bundle Validator`**, with a description under 125
  characters. The Marketplace listing form rejects the old metadata: "Validate
  OKF bundle" collides with an existing action, user or org name, and the
  description was over the limit. Consumers pin
  `scaccogatto/okf-skills@<tag>`, not the display name, so nothing breaks.

### Added
- CI: **releases follow the version bump automatically**
  (`.github/workflows/release.yml`). Releasing was a manual `gh release create`
  and it got skipped: 0.7.0 and 0.7.1 were bumped in `plugin.json` and never
  released. A push to `main` touching `plugin.json` now tags and publishes
  `okf--v<version>`, idempotently.
- CI: **the bump itself is mandatory.** Auto-release only fires on a bump, so a
  PR touching the shipped surface (`.claude-plugin/`, `skills/`, `hooks/`,
  `templates/`, `action.yml`) fails unless `plugin.json`'s version is strictly
  greater. Docs, `.okf/`, tests and CI are exempt, and the `skip-version-check`
  label bypasses it. The job always runs and handles the bypass inside the step,
  because a job skipped by a job-level `if` reports no status and would wedge
  the merge once the check is required.
- CI: `GITHUB_TOKEN` pinned to `contents: read` where write is not needed.

## [0.7.1] — 2026-08-03

### Fixed
- **The Stop hook no longer counts untracked files as uncommitted changes.** It
  false-fired on its first real trigger (this repo: session worktrees under
  `.claude/`). Excluding `.claude/` would have been a symptom patch, since
  `.venv/`, `.DS_Store` or a build dir would false-fire the same way in a
  consumer repo, so the gate now ignores every untracked path (`grep -v '^??'`)
  and matches its own intent: a brand-new untracked file is not yet a documented
  asset with a concept to update. Stated tradeoff, a new file that ought to get
  a concept no longer triggers the nudge; authoring is the maintain flow's job.

### Removed
- **The `benchmark/` tree is gone**, with the README badge, differentiator and
  "Does it actually help" section that pointed at it. It measured better answers
  and cheaper reading, which is the ecosystem's adoption pitch, not this
  standard: the vendored SPEC.md §1 states its intent as portable, diffable,
  trustable knowledge and never mentions tokens, cost or answer quality.
  Removed with it, the with/without run, its reframes, and the repetition
  protocol that was written in this same release and never run.

### Docs
- README reordered example-first and cut from 289 to 229 lines: the
  knowledge-as-code comparison table, the duplicated trust-tier explanation and
  the re-taught normative detail are gone, the reference material is not.
- The Stop-hook section had described the gate as "uncommitted changes"; it now
  says modified tracked files, notes that the opt-in flag must sit in the
  frontmatter, and links the stop-hook concept for the gate sequence and known
  limits instead of duplicating them.

## [0.7.0] — 2026-08-02

### Added
- **A dormant Stop hook** (`hooks/hooks.json`, `hooks/okf-stop-check.sh`). The
  plugin now ships a hook on Stop that does nothing unless the bundle opts in
  with `upkeep: enforced` in `.okf/index.md` frontmatter and the user has not
  set `OKF_HOOK=off`. When armed it blocks Stop if the tree has uncommitted
  changes while `.okf/log.md` was not touched: a bundle rots in exactly the
  session that forgets it, and a reminder that only exists on the maintainer's
  machine is not shipped enforcement. The flag counts only inside the
  frontmatter, not anywhere in the file, and the `stop_hook_active` loop guard
  is plain `grep`, not `jq`, because a missing `jq` must never disable the guard
  and re-block forever. Supersedes the `no-hooks` decision, now deprecated, with
  `dormant-hooks`.

### Docs
- `demo.gif` re-recorded on the v0.2 detail panel (the old one still showed the
  v0.1 header and none of what v0.2 added) and walks three trust tiers, ending
  on a derivation edge reached through SOURCES. Recording it surfaced a real
  layout bug, fixed here: `#app` left its grid row implicit, so a long concept
  body stretched the panel past the viewport and the page grew its own
  scrollbars. Both live pages had them.
- README leads with the two claims that are true and unique today (the toolkit
  is on v0.2 while the other tools in Google's community list were on v0.1 when
  checked, with the date of the check, since that claim quietly goes false), and
  the action example is pinned to `@v1` rather than `@main`.
- The social preview still said "OKF v0.1 spec" and had no source, so it aged
  through two spec versions unnoticed. Its source is now `docs/assets/og.html`
  and it is regenerated with headless Chrome at 2x, the invocation recorded in
  the file header. Not a `make` target: it needs a browser and changes about
  twice a year. The header also records the part that is easy to miss, that
  GitHub serves an uploaded copy, so regenerating the PNG does nothing until it
  is re-uploaded under Settings.

## [0.6.0] — 2026-07-27

### Added
- **`visualize` derives the §5.3 trust tier and staleness.** The panel showed the
  raw fields; it now shows what they mean — *unverified* / *machine-confirmed* /
  *human-reviewed*, and a stale badge once `stale_after` is past. Both are
  computed at render time: OKF deliberately stores neither, because a stored tier
  is a stored opinion and it goes stale. Advisory badges, never a gate (§5.3).
- **`validate` checks the §7 actor convention** on `generated.by`,
  `verified[].by` and `sources[].author`. Not a whitelist — the spec's own §5.1
  example uses `author: team:ga4-docs`, so the `<prefix>:<id>` family is open.
  What it catches is the near-miss of `human:`: `Human:dana` satisfies the generic
  shape and looks well-formed while §5.3 reads it as an agent, silently demoting a
  concept a person did review.
- **`usage_window`** is validated (a `usage_count` with nothing framing it warns;
  bounds must be absolute dates) and rendered next to the count it frames — a
  count without its window is a number without units (§5.1).
- **Attested Computation path-valued fields** — `computation`,
  `executor.resource`, `attester.resource` — are resolved when they point inside
  the bundle (§6.2). They are exactly the pointer that rots: the concept keeps
  validating while the script it names moves away.
- **`generated.at` / `verified[].at` are checked as RFC 3339**, date-only
  tolerated, with the same quoted/unquoted equivalence as `stale_after`.
- **A composite GitHub Action** (`action.yml`): gate a bundle in any repo's CI
  without Claude Code. Exercised in CI on both the passing and the failing path,
  since an action that never fails looks green for the wrong reason.

## [0.5.0] — 2026-07-27

### Changed
- **The toolkit now targets OKF v0.2.** `skills/okf/reference/SPEC.md` is
  re-vendored verbatim from upstream `3fcbb9f`, and the `okf`, `validate`, and
  `visualize` skills apply its rules. Conformance is unchanged in substance
  (parseable frontmatter with a non-empty `type`) but has moved from §9 to §11;
  validator messages cite v0.2 section numbers throughout.
- `okf_init.py` scaffolds v0.2 frontmatter — `okf_version: "0.2"` in the root
  index, `status` and `generated: {by, at}` (actor `process:okf_init`) on the
  starter concept.
- `examples/sample-bundle` and this repo's own `.okf` bundle are migrated to
  v0.2; the two GitHub Pages demos are regenerated from them. The sample bundle's
  checkout conversion metric now records the orders database in `sources`, so the
  live demo shows a derivation edge.

### Added
- `validate`: checks for the new families, all soft — `generated.by` present,
  every `verified` entry has an actor (a bare mapping counts as a one-element
  list, §5.2), `status` is one of draft/stable/deprecated, `stale_after` and
  `sources[].last_modified` are absolute `YYYY-MM-DD` dates, every `sources`
  entry has a `resource`, every `[^label]` footnote names a `sources[].id`, and
  an `Attested Computation` declares a `runtime`.
- `visualize`: the detail panel renders `status`, `generated`, `verified`,
  `stale_after`, and a Sources list with each source's credibility signals; a
  `sources` entry pointing at another concept in the bundle also becomes a graph
  edge.
- `validate --migrate`: rewrites a v0.1 bundle to v0.2 in place — `timestamp` to
  `generated: { by: process:okf-migrate, at }`, a `# Citations` list up into
  `sources`, `okf_version` to 0.2. Textual, so comments, key order and quoting
  survive a migration; idempotent, so a half-migrated bundle converges. It does
  not invent `generated.by` for pre-v0.2 content (the `process:` actor leaves the
  concept correctly *unverified* under §5.3) and cannot recover per-claim
  `[^id]` attribution, which v0.1 never encoded — the command says so.
- `validate --max-warnings N`: the gate between a default that fails on nothing
  and a `--strict` that demands zero, so a bundle with known warnings can still
  be gated in CI. `--strict` is the `N=0` case.
- `make docs` pins the exact invocation behind the two GitHub Pages demos, and CI
  fails on a stale `docs/`. They had silently drifted: both live pages were
  serving a build from before the DOMPurify sanitize fix.

### Compatibility
- **v0.1 bundles still validate and render.** The two superseded constructs are
  read, not rejected: a legacy `timestamp` is used as `generated.at`, and a body
  `# Citations` list is recognized. Both are reported as warnings naming their
  v0.2 replacement (§13.1).
- **`--strict` fails an unmigrated v0.1 bundle.** That is the migration nudge and
  it is deliberate — `templates/CLAUDE-okf.md` tells every user to run `--strict`
  before committing, so `--migrate` ships in the same release to make it a door
  rather than a wall. Note that §11 conformance itself never mentioned
  `timestamp` or `# Citations`: a v0.1 bundle is conformant under v0.2 either way.

## [0.4.0] — 2026-07-17

### Added
- `okf`: new `skills/okf/scripts/okf_init.py` scaffolds a conformant starter
  bundle (`index.md`, `log.md`, a `getting-started.md` concept with full
  recommended frontmatter) in one shot — `okf_init.py <target-dir> [--title
  "..."] [--force]`. Refuses to touch a directory that already has `.md`
  files unless `--force`. CI asserts the scaffold passes `okf_validate.py
  --strict` with zero warnings.

## [0.3.6] — 2026-07-17

### Security
- `visualize`: fixed a stored XSS — a concept body's rendered markdown was
  assigned to `innerHTML` via `marked.parse()` with no sanitization, so a
  concept file containing e.g. `<img src=x onerror=alert(1)>` executed when
  the concept was selected. The output of `marked.parse()` is now passed
  through [DOMPurify](https://github.com/cure53/DOMPurify) (loaded from the
  same jsdelivr CDN as Cytoscape/marked, pinned to an exact version with an
  SRI `integrity` hash) before assignment.

### Fixed
- `validate`/`visualize`: a binary or non-UTF-8 `.md` file no longer crashes
  the whole run — `validate` reports it as a per-file error, `visualize` skips
  it with a stderr warning and drops it from the graph.

### Added
- CI: a `windows-latest` job runs the validator against
  `examples/sample-bundle` without `PYTHONUTF8` set — real regression coverage
  for the cp1252 class of bug (the existing cp1252 step only simulates it on
  Linux).
- CI: a self-test asserting the visualizer's DOMPurify hook is wired in and
  wraps `marked.parse(...)`.

### Docs
- `marketplace.json`: the plugin description now mentions `visualize`
  alongside author/maintain/validate.
- `README.md`: a compact Install block (plugin one-liner + skills.sh
  one-liner) now sits right under the badges/demo GIF; the full Install
  section is unchanged.

## [0.3.5] — 2026-07-17

### Fixed
- `validate`/`visualize`: no longer crash with `UnicodeEncodeError` on default
  Windows consoles (cp1252) — stdout/stderr are reconfigured to UTF-8 so the
  ✓/✗/— glyphs always print. Thanks @crackcode09 (#3). A cp1252 regression
  step now runs in CI.
- `visualize`: large bundles no longer freeze the browser. The default force
  (cose) layout — measured at ~32 s of blocked main thread for a ~2k-concept
  bundle, and extrapolating to hours at 20k+ — now applies only up to 1,000
  concepts; larger bundles default to the linear `concentric` layout (explicit
  `--layout cose` still wins, and the in-page layout picker asks before running
  force on a large graph).
- `visualize`: search/filter passes are wrapped in `cy.batch()` and the search
  box is debounced (150 ms) — previously every keystroke ran an unbatched
  style-write pass over all nodes (~1.8 s per keystroke at 23k concepts).

### Added
- Unit tests for `okf_validate.py` internals (frontmatter parsing, concept/index/log checks, link collection and resolution) — 25 cases, stdlib
  `unittest`, wired into CI (#1).
- `visualize`: warns above 5,000 concepts (slow page, unreadable hairball) and
  suggests rendering a subtree; new `--max-nodes N` refuses oversized bundles
  outright, for CI use.
- Decision record: [scale guardrails](.okf/decisions/scale-guardrails.md).

## [0.3.4] — 2026-07-06

### Fixed
- `visualize`: a concept body containing a literal `</script>` no longer truncates
  the inline `NODES`/`EDGES` data script and kills the page — reported and first
  fixed in [#2](https://github.com/scaccogatto/okf-skills/pull/2) by
  [@delossantosleandro](https://github.com/delossantosleandro); the escaping is now
  hardened to `<` → `\u003c`, which also neutralizes `<!--`/`<script` (the
  script-data escaped states) in one stroke and keeps the payload valid JSON.
- `visualize`: template placeholders are substituted in a single pass, so a concept
  body that mentions `__EDGES__` (or any other marker) can no longer have the edges
  JSON spliced into it.

### Changed
- CI self-test for the visualizer now asserts on outcomes (no raw `</script>`,
  `<!--<script` or clobbered `__EDGES__` in the output) rather than on one specific
  escaping strategy.

## [0.3.3] — 2026-06-28

### Added
- **Dogfooding:** the repo now documents itself in OKF at [`.okf/`](.okf/) — 9
  cross-linked concepts (skills, components, the vendored spec, and architectural
  decisions), rendered as a second live demo (`docs/self.html`).
- CI validates the repo's own `.okf/` bundle (strict) on every push, alongside the
  example bundle.

## [0.3.2] — 2026-06-28

### Added
- `visualize`: `--og-image` flag emits Open Graph + Twitter Card meta, so a shared
  `viz.html` (e.g. the live demo) renders a rich preview card instead of a bare
  link. The hosted demo now advertises the project's social card.

## [0.3.1] — 2026-06-28

### Added
- `visualize`: `--layout` flag and `?layout=` / `?select=` URL params — set the
  initial layout and pre-select a concept, so a specific view is shareable by link
  (also powers the animated README demo).

### Changed
- Default the live demo to the `breadthfirst` layout and use it for the README
  hero (now an animated GIF) — the force layout was too crowded for a small bundle.

## [0.3.0] — 2026-06-28

### Added
- `visualize`: `--title` / `--link` flags — name the graph and show a clickable
  back-link to the source repo in the header.
- `visualize`: **deep-linkable concepts** — `viz.html#services/auth-api` loads with
  that concept already selected; selecting a node updates the URL hash so any
  concept is shareable by link.
- Richer `examples/sample-bundle`: 8 cross-linked concepts spanning `Service`,
  `Schema`, `Decision`, `Runbook`, and `Metric` — the bundle behind the live demo.
- GitHub Pages **live demo** (`docs/`) rendering the sample bundle as an
  interactive graph.

### Changed
- `visualize`: cap zoom and add label outlines so small or dense graphs stay
  legible on first render instead of over-zooming into overlapping labels.

## [0.2.1] — 2026-06-18

### Fixed
- `visualize`: `okf_visualize.py` no longer crashes with
  `TypeError: Object of type date is not JSON serializable` on bundles whose
  `timestamp:` (or any) frontmatter is an unquoted ISO 8601 value — PyYAML parses
  these into `date`/`datetime` objects. `json.dumps` of the node/edge graph now
  passes `default=str`, serializing them as strings.

## [0.2.0] — 2026-06-14

### Added
- `visualize` skill bundling `okf_visualize.py`: renders a bundle to a single
  self-contained `viz.html` — force/concentric/breadth-first/circle/grid layouts,
  per-type filter + clickable legend, search, neighbour highlight, and a wiki-style
  detail panel with rendered markdown plus "Links to" / "Cited by" backlinks.
  Referenced via `${CLAUDE_SKILL_DIR}` (works as plugin or standalone skills.sh skill).

## [0.1.0] — 2026-06-14

### Added
- `okf` skill: produce / maintain / consume OKF bundles, driven by the verbatim
  v0.1 spec and copy-ready templates.
- `validate` skill bundling `okf_validate.py`: deterministic §9 conformance
  checker (PEP 723 / `uv`, JSON and `--strict` modes), referenced via
  `${CLAUDE_SKILL_DIR}` so it works as a plugin or a standalone skills.sh skill.
- Dual distribution: Claude Code plugin marketplace **and** skills.sh
  (`npx skills add`) from the same repo.
- Verbatim OKF v0.1 spec vendored at `skills/okf/reference/SPEC.md`
  (upstream `ee67a5c`, Apache-2.0).
- `templates/CLAUDE-okf.md`: adoption snippet enabling soft-mode consume/maintain.
- `examples/sample-bundle/`: a conformant reference bundle.
- One-plugin marketplace manifest for `/plugin marketplace add scaccogatto/okf-skills`.
- CI: validates the plugin manifest and the example bundle on every push.
