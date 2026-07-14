# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this plugin tracks the
OKF spec version it supports.

## [Unreleased]

### Fixed
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
