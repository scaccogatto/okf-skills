---
type: Tool
title: okf_validate.py
description: Zero-config Python v0.3 conformance checker and v0.1/v0.2→v0.3 migrator (PEP 723 / uv, PyYAML).
resource: https://github.com/ekar-is/okf-skills/blob/main/skills/validate/scripts/okf_validate.py
tags: [python, validator, uv]
status: stable
generated: { by: "claude/opus-5.5", at: "2026-11-26T00:00:00Z" }
---

# Overview

The deterministic engine behind the [validate skill](/skills/validate.md). A
single self-describing script (dependencies declared inline via PEP 723) that
parses every non-reserved `.md` file and enforces the hard rules of
[OKF v0.3 §11.1](/reference/okf-spec.md). The same rules are shared with the
[MCP server](/components/mcp-server.md) and the
[visualizer](/components/visualizer.md), and `tests/test_conformance_parity.py`
checks that the three agree.

Errors:

* every frontmatter block parses as a YAML mapping, including the root
  `index.md`.
* a subdirectory `index.md` (§8) or a `log.md` (§9) whose leading block parses
  as a non-empty YAML mapping: they have no frontmatter. A leading block that
  is not a mapping at all breaks §11.1 rule 1 instead. `---` horizontal rules
  around markdown that YAML reads as empty (a heading) are not flagged. A subdirectory `index.md`
  declaring `okf_version` is named as a nested bundle root, to be validated
  separately.
* a duplicate key at any level, a value PyYAML cannot build (an impossible date
  such as `2026-02-30`) and runaway nesting are errors.
* a `## ` heading of a `log.md` that looks like a date in a non-ISO or
  impossible form (`22/05/2026`, `May 22, 2026`, `2026-5-2`, `2026-13-45`): three
  numeric groups joined by `/`, `-` or `.`, or an English month name next to a
  1-2 digit day and a 4-digit year. Any other non-date heading (`## Unreleased`,
  `## 2026-05-21 (hotfix)`) is a warning: §9 constrains date headings, not every
  heading.
* a file that is not UTF-8.

A `.md` file without frontmatter, or whose `type` is not a non-empty string, is
not a concept (§3.2), so it is skipped with a **warning**, not an error. That is
how a `README.md` or an `AGENTS.md` can share the bundle directory. Dot-paths
(`.git`, `.github`) are skipped entirely.

# Checks beyond the hard rule

All soft, all warnings: `generated.by` present when `generated` is, and every
`verified` entry has both `by` and `at` (a bare mapping counts as a one-element
list). `status` is one of draft/stable/deprecated, and `superseded_by` resolves.
Timestamps (`generated.at`, `verified[].at`, `stale_after`,
`sources[].last_modified`, `usage_window`) must be real dates or RFC 3339
date-times with an offset and seconds. A date-time without an offset, an
impossible date, or an instant outside years 1-9999 once read in UTC
(`0001-01-01T00:00:00+05:00`) is invalid.
Every `sources` entry has a `resource`, and a `usage_count` is framed by a
`usage_window`. Every `[^label]` footnote names a `sources[].id` (code spans and
fenced blocks are skipped, as CommonMark does, so a regex class like `[^a-z]` in
code is not a footnote). An `Attested Computation` declares a `runtime`, its
`parameters` entries carry `name` and `type`, and its path-valued `computation`,
`executor.resource` and `attester.resource` resolve.

Recommended-field warnings (`title`, `description`, `tags`, `generated`) are
labelled `okf-skills lint` and emitted only with `--lint`: they are this
plugin's house style, not the spec, and a concept with only `type` is
conformant and passes `--strict`.

Path fields follow §6: a value without a leading `/` resolves from its file's
directory. They include `superseded_by`, the Attested Computation fields, and
top-level `resource` and `sources[].resource`. Since those two may be a URI, a
scope descriptor or an opaque identifier, they are paths only when rooted or
dot-relative (`/`, `./`, `../`), or when they have no whitespace and name an
existing file (not a directory) from the file's directory or, in a legacy
bundle, from the root. Anything else (`proj.ds.users`, `example.com`) is opaque:
no warning, no `--migrate` rewrite, no graph edge. A bundle declaring `okf_version` 0.2 or none also gets the §12.1 root
fallback, so a legacy bundle is not flooded with warnings. External targets
(a URI scheme) and targets outside the bundle root are not bundle paths.

Cross-links are scanned in the body only, with code spans and fenced blocks
stripped, and reference-style links (`[label]: target`) are included. Footnote
definitions are not links. A broken link is a warning, never an error (§6.1).

The root `index.md` frontmatter is checked against the §8.1 keys (`okf_version`,
`title`, `description`, `license`) and `x-` extension keys, which covers the
plugin's own `x-okf-skills-upkeep` and `x-okf-skills-recursive` (the Stop hook's
flags, so an enforced-upkeep bundle passes its own `--strict` run). The old
unprefixed `upkeep` and `recursive` are deprecated and warn, naming the
replacement. `okf_version` must be quoted and match the checked version. Legacy
`timestamp` and `# Citations` warn with their replacement, per the
[v0.3 decision](/decisions/okf-v03-target.md).

# The actor check (§7)

Deliberately not a whitelist — the spec's own §5.1 example uses
`author: team:ga4-docs`, so the `<prefix>:<id>` family is open. What is caught is
the one failure that is silent: a near-miss of `human:`. `Human:dana` satisfies
the generic shape and looks well-formed, while §5.3 keys trust tiers off that
exact lowercase prefix and reads it as an agent. An actor with leading or
trailing whitespace (` human:a`) is a near-miss too, since consumers match
`human:` exactly. `humanoid_agent/v1` is not a near-miss and passes.

# Migration (`--migrate`)

The only mode that writes. Rewrites v0.1 and v0.2 constructs in place to v0.3,
on concepts only:

* a top-level `timestamp` becomes `generated: { by: process:okf-migrate, at }`
  when there is no `generated`, accepted only if the re-parsed result differs
  by exactly that, and a `# Citations` list moves up into `sources`.
* in a bundle declaring 0.2 or none, block-style path fields that were
  root-only under §12.1 get a `/` prefix: `superseded_by`, top-level `resource`,
  `sources[].resource` and the Attested Computation fields. Nothing that already
  resolved from its own directory is touched, nor an opaque `resource`, nor a
  value with leading or trailing whitespace (left, warned, and still pending).
* in the root index, `upkeep` and `recursive` are renamed to
  `x-okf-skills-upkeep` and `x-okf-skills-recursive` (never onto an existing key),
  with a note that collaborators on okf-skills 0.12 or older must update the
  plugin, since older Stop hooks read only the old key.
* `okf_version` is bumped to 0.3 only when no root-only path field remains in the
  bundle, otherwise the version stays and the leftovers are listed.

The rewrite is **textual**: a PyYAML round-trip would flatten comments, key order
and quoting across the whole bundle. CRLF endings and a BOM are kept, and a file
that mixes CRLF and LF is refused. Every rewrite is verified by re-parsing: if
the result differs from the original in anything but the intended `/` prefixes,
the file is left untouched and named in a warning. Values are never stringified
as containers, so an alias bomb in a bundle cannot blow up the check. Each branch
is guarded on the newer key already existing, so a half-migrated bundle converges
instead of growing a duplicate key. After rewriting, the bundle is validated. See
the [v0.3 decision](/decisions/okf-v03-target.md) for what is deliberately not
recovered.

# Output

| Signal | Meaning |
|--------|---------|
| `ERROR` | Hard §11.1 failure, the bundle is non-conformant. |
| `warn`  | Soft guidance: spec-level (malformed family, broken link, legacy or deprecated field, skipped non-concept) and, with `--lint`, `okf-skills lint` (plugin house style such as missing recommended fields). |

Exit code is non-zero on any error, or when warnings exceed the gate: `--strict`
allows none, `--max-warnings N` allows N, the default allows any. When only the gate fails, the last line says so
(`✓ conformant, but --strict allows no warnings (2 found)`). The gate
counts emitted warnings, so lint counts only under `--lint`. `--json` emits
machine-readable output for CI, including whether `lint` was on.
