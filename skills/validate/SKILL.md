---
name: validate
description: >-
  Check that an Open Knowledge Format (OKF) bundle is conformant with the v0.2
  spec (§11). Use when asked to validate, lint, or check an OKF bundle, or before
  committing changes to one. Runs a deterministic Python checker — not an
  eyeball pass.
user-invocable: true
argument-hint: "[bundle-dir] [--strict]"
allowed-tools: Bash
---

# Validate an OKF bundle

Run the deterministic conformance checker against the target bundle. Default to
the project's `.okf/` directory when no path is given.

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" $ARGUMENTS
```

If `uv` is unavailable, fall back to:

```bash
python3 -m pip install --quiet pyyaml && \
python3 "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" $ARGUMENTS
```

`${CLAUDE_SKILL_DIR}` resolves whether this skill runs as part of the `okf`
plugin or is installed standalone (e.g. via `npx skills add`), so the checker is
always found alongside the skill.

Interpret the result:

- **ERROR** → a hard §11 conformance failure (no parseable frontmatter, or a
  missing/empty `type`). The bundle is non-conformant. Fix every one.
- **warn** → soft guidance (missing recommended field, non-ISO log date, broken
  cross-link, a malformed v0.2 family, a footnote naming no source). Never
  blocks; broken links in particular are explicitly tolerated by the spec
  (§6.1). Fix when cheap.

v0.1 bundles validate too: a legacy `timestamp` or `# Citations` section is
reported as a warning naming its v0.2 replacement (`generated.at`, `sources`),
never as an error (§13.1). Under `--strict` those warnings do fail the run —
that is the migration nudge.

Exit code is non-zero if any error is present (or any warning, when `--strict`).
Add `--json` for machine-readable output (useful in CI).
