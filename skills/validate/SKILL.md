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

- **ERROR** → a hard §11.1 conformance failure. The bundle is non-conformant.
  Fix every one. It covers:
  - rule 1: a frontmatter block that is not valid YAML, is not a mapping,
    repeats a key, or holds a value no parser can build (an impossible date such
    as `2026-02-30`, nesting too deep) (§4).
  - rule 2: an `index.md` below the bundle root or a `log.md` whose leading
    block parses as a non-empty YAML mapping (§8, §9: they have no
    frontmatter). A leading block that is not a mapping at all breaks
    rule 1. Only `---` horizontal rules around markdown that YAML reads as
    empty (a heading, nothing) are fine. A subdirectory
    `index.md` declaring `okf_version` looks like a nested bundle root:
    validate that directory separately. Also a `log.md` `## ` heading that
    looks like a date but is not ISO 8601 `YYYY-MM-DD` (`22/05/2026`,
    `May 22, 2026`, `2026-5-2`, `2026-13-45`, §9).
  - a file the checker cannot read as UTF-8.
- **warn** → soft guidance. Never blocks without a gate. Fix when cheap. It
  covers:
  - a `.md` file with no frontmatter or no string `type`: not a concept,
    skipped (§3.2). Fine for a `README.md` or `AGENTS.md`. On a file meant as
    knowledge, add a `type`.
  - `okf-skills lint`: a concept without `title`, `description`, `tags` or
    `generated`. This is the plugin's discovery advice, not the spec: a concept
    with only `type` is fully conformant (§4.1).
  - a broken cross-link, read from the body only: inline `[text](target)` and
    reference definitions `[label]: target` (footnotes `[^x]:` are not links).
    The spec explicitly tolerates these (§6.1). A link or path that resolves
    outside the bundle is external and never checked.
  - a malformed family: a timestamp that is neither a real date nor a real
    date-time with an offset (§5), a `verified` event missing `by` or `at` (§5.2), an unknown
    `status`, matched exactly so ` stable ` or `false` is unknown (consumers
    treat it as not current, §5.4), `superseded_by` on a
    concept that is not deprecated, a footnote naming no source (§5.1).
  - an actor that misses the §7 shapes, or carries leading or trailing
    whitespace.
  - a `log.md` `## ` heading that is not a date at all (`## Unreleased`,
    `## 2026-05-21 (hotfix)`): §9 constrains date headings only.
  - an Attested Computation missing `runtime`, or a `parameters` entry without
    `name` and `type` (§10.2).
  - a path field (§6.2) that resolves nowhere: `superseded_by`, and on an
    Attested Computation `computation`, `executor.resource`, `attester.resource`.
    Top-level `resource` and `sources[].resource` are checked too, but since
    they may be a URI, a scope descriptor or an opaque identifier, they are
    paths only when rooted or dot-relative (`/`, `./`, `../`), or when they
    have no whitespace and name an existing file (not a directory) from the
    file's directory or, in a legacy bundle, from the root. Anything else
    (`proj.ds.users`, `example.com`) is opaque and never warned about.
  - a root `index.md` with an unquoted `okf_version`, a key outside §8.1 that
    does not use the `x-` extension prefix, or a declared `okf_version` other
    than `"0.3"`: older ones are checked with the §12.1 fallbacks, newer ones
    best-effort as v0.3 (§12).
  - a deprecated plugin key `upkeep` or `recursive` in the root `index.md`:
    rename it to `x-okf-skills-upkeep` / `x-okf-skills-recursive` (§4.1 keeps
    unprefixed keys for future OKF versions). `--migrate` does it.

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
- v0.2 (or no `okf_version`, or an empty one): a bare path field that
  resolves only from the bundle root is read with the §12.1 fallback and
  reported. Both path forms are valid in v0.3 (§13.2), but v0.3 resolves a
  bare value from the file's directory, so this one needs the `/` form to keep
  its meaning once the bundle declares 0.3.

Under `--strict` those warnings do fail the run. That is the migration nudge,
and `--migrate` is the door.

## Migrating to v0.3

`--migrate` **rewrites the bundle in place** before validating: the one mode of
this skill that is not read-only, so say what it will touch before running it on
a bundle the user has not asked to migrate. It is textual (comments, key order,
quoting, CRLF line endings and a BOM survive) and idempotent.

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" .okf --migrate --strict
```

What it does, on concepts only (frontmatter with a string `type`):

- In a bundle declaring 0.2 or earlier (or no version), prefixes with `/` every
  block-style path field that resolves only from the bundle root: top-level
  `resource` and `superseded_by`, each `sources[].resource`, and on an Attested
  Computation `computation` and the direct `resource` child of `executor` /
  `attester`. A bundle that already declares 0.3 gets no path rewrite.
- Hoists a v0.1 top-level `timestamp` to `generated: { by: process:okf-migrate, at }`
  when there is no `generated`, and lifts a v0.1 `# Citations` list into `sources`.
  An opaque `resource` (see above) is never rewritten.
- In the root `index.md`, renames `upkeep` / `recursive` to
  `x-okf-skills-upkeep` / `x-okf-skills-recursive` (collaborators on
  okf-skills 0.12 or older must then update the plugin: older Stop hooks read
  only the old key), and bumps a declared
  `okf_version` of 0.1 or 0.2 to `"0.3"` (a trailing comment is kept), but
  only once no root-only path field remains anywhere in the bundle. Otherwise
  the version stays, the remaining fields are listed, and `--strict` fails.
  A bundle that declares no version is not given one.

What it refuses to rewrite, with a warning naming the file: a concept whose
rewritten frontmatter would parse to anything other than the original with
just the `/` added (the guard against block scalar text or odd indentation
that looks like a field), a `timestamp` hoist with the same problem, a path
value with leading or trailing whitespace (it stays pending), a root index with
the same problem, and a file that mixes CRLF and LF line endings. It never renames a plugin key onto one that
already exists.

Limits worth repeating to the user: path fields written in flow style
(`executor: { resource: x }`) are left alone and keep warning (and block the
version bump), `generated.by` cannot be recovered for pre-v0.2 content (hence
the `process:` actor, so the concept stays correctly `unverified` under §5.3),
and per-claim `[^id]` attribution was never encoded in v0.1, so only the source
list moves up.

## Exit codes

Non-zero if any error is present, or if warnings exceed the gate:
`--strict` allows none, `--max-warnings N` allows N, the default allows any.
Add `--json` for machine-readable output (useful in CI).
