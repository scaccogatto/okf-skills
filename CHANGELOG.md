# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this plugin tracks the
OKF spec version it supports.

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
