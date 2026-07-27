# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this plugin tracks the
OKF spec version it supports.

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
