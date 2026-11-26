---
name: validate
description: >-
  Check that an Open Knowledge Format (OKF) bundle is conformant with the v0.3
  spec (§11). Use when asked to validate, lint, or check an OKF bundle, or before
  committing changes to one. Runs a deterministic Python checker — not an
  eyeball pass. Also migrates a v0.1 or v0.2 bundle to v0.3 in place with
  `--migrate`.
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

- **ERROR** → a hard §11.1 conformance failure: a frontmatter block that is not
  valid YAML, is not a mapping, or repeats a key (§4), or a file the checker
  cannot read as UTF-8. The bundle is non-conformant. Fix every one.
- **warn** → soft guidance. Never blocks without a gate. Fix when cheap. It
  covers:
  - a `.md` file with no frontmatter or no `type`: not a concept, skipped
    (§3.2). Fine for a `README.md` or `AGENTS.md`. On a file meant as
    knowledge, add a `type`.
  - a missing recommended field, a non-ISO log date, frontmatter in a reserved
    file (§8, §9).
  - a broken cross-link. The spec explicitly tolerates these (§6.1). A link or
    path that resolves outside the bundle is external and never checked.
  - a malformed family: a timestamp that is neither a date nor a date-time with
    an offset (§5), a `verified` event missing `by` or `at` (§5.2), an unknown
    `status` (consumers treat it as not current, §5.4), `superseded_by` on a
    concept that is not deprecated, a footnote naming no source (§5.1).
  - an actor that misses the §7 shapes.
  - an Attested Computation missing `runtime`, a `parameters` entry without
    `name` and `type`, a path field (`computation`, `executor.resource`,
    `attester.resource`, `superseded_by`) that resolves nowhere (§6.2, §10.2).
  - a root `index.md` with an unquoted `okf_version`, a key outside §8.1
    that does not use the `x-` extension prefix, or a different declared
    `okf_version` (§12).

Files and directories whose names start with `.` are not part of the bundle
(§3.2) and are never read. The bundle root itself may be `.okf/`.

One warning is worth more than the others: a §7 near-miss such as `Human:dana`
or `human/dana`. §5.3 keys trust tiers off the exact lowercase `human:` prefix,
so the concept silently reads as machine-confirmed when a person did review it.
Fix that one on sight.

## Older bundles

v0.1 and v0.2 bundles validate too, and never fail on version alone:

- v0.1: a legacy `timestamp` or `# Citations` section is a warning naming its
  replacement (`generated.at`, `sources`), see Appendix B.
- v0.2 (or no `okf_version`): a bare path field that resolves only from the
  bundle root is read with the §12.1 fallback and reported, asking for the
  `/` form. v0.3 resolves bare values from the file's directory.

Under `--strict` those warnings do fail the run. That is the migration nudge,
and `--migrate` is the door.

## Migrating to v0.3

`--migrate` **rewrites the bundle in place** before validating: the one mode of
this skill that is not read-only, so say what it will touch before running it on
a bundle the user has not asked to migrate. It is textual (comments, key order
and quoting survive) and idempotent.

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" .okf --migrate --strict
```

It bumps `okf_version` to `"0.3"`, prefixes with `/` every block-style path
field that resolves only from the bundle root, hoists a v0.1 `timestamp` to
`generated: { by: process:okf-migrate, at }`, and lifts a v0.1 `# Citations`
list into `sources`. Limits worth repeating to the user: path fields written in
flow style (`executor: { resource: x }`) are left alone and keep warning,
`generated.by` cannot be recovered for pre-v0.2 content (hence the `process:`
actor, so the concept stays correctly `unverified` under §5.3), and per-claim
`[^id]` attribution was never encoded in v0.1, so only the source list moves
up.

## Exit codes

Non-zero if any error is present, or if warnings exceed the gate:
`--strict` allows none, `--max-warnings N` allows N, the default allows any.
Add `--json` for machine-readable output (useful in CI).
