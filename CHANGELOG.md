# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this plugin tracks the
OKF spec version it supports.

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
- One-plugin marketplace manifest for `/plugin marketplace add scaccogatto/okf`.
- CI: validates the plugin manifest and the example bundle on every push.
