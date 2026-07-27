---
name: validate
description: >-
  Check that an Open Knowledge Format (OKF) bundle is conformant with the v0.2
  spec (§11). Use when asked to validate, lint, or check an OKF bundle, or before
  committing changes to one. Runs a deterministic Python checker — not an
  eyeball pass. Also migrates a v0.1 bundle to v0.2 in place with `--migrate`.
user-invocable: true
argument-hint: "[bundle-dir] [--strict | --max-warnings N] [--migrate]"
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
that is the migration nudge, and `--migrate` is the door.

## Migrating a v0.1 bundle

`--migrate` **rewrites the bundle in place** before validating — the one mode of
this skill that is not read-only, so say what it will touch before running it on
a bundle the user has not asked to migrate. It is textual (comments, key order
and quoting survive) and idempotent.

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" .okf --migrate --strict
```

It hoists `timestamp` to `generated: { by: process:okf-migrate, at }`, lifts a
`# Citations` list into `sources`, and bumps `okf_version`. Two limits worth
repeating to the user: `generated.by` cannot be recovered for pre-v0.2 content
(hence the `process:` actor — the concept stays correctly `unverified` under
§5.3), and per-claim `[^id]` attribution was never encoded in v0.1, so only the
source list moves up.

## Exit codes

Non-zero if any error is present, or if warnings exceed the gate:
`--strict` allows none, `--max-warnings N` allows N, the default allows any.
Add `--json` for machine-readable output (useful in CI).
