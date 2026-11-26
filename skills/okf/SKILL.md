---
name: okf
description: >-
  Author, maintain, and consume Open Knowledge Format (OKF) knowledge bundles —
  portable markdown + YAML frontmatter that both humans and agents read. Use when
  capturing project knowledge (services, APIs, schemas, metrics, runbooks,
  decisions) into an OKF bundle, when updating one after code or docs change, or
  when a repository contains an `.okf/` (or other OKF) bundle that should inform
  the task. Triggers on: "document this in OKF", "update the knowledge bundle",
  "capture this as a concept", or any work in a repo that has an OKF bundle.
user-invocable: true
argument-hint: "[produce|maintain|consume] [path]"
allowed-tools: Read Write Edit Grep Glob Bash
---

# Open Knowledge Format (OKF) skill

OKF represents knowledge as a directory of markdown files with YAML frontmatter.
It is minimal by design: no schema registry, no runtime, no SDK. Your job is to
produce, maintain, and consume OKF bundles **conformant with the spec**, not your
memory of it.

**Always read the canonical spec before non-trivial work:**
[reference/SPEC.md](reference/SPEC.md). It is the verbatim OKF v0.3 specification
and the source of truth for every rule below.

## The hard rules

A bundle is conformant (§11.1) when every frontmatter block parses as a YAML
mapping (no duplicate keys, no custom tags) and the reserved files follow §8
and §9. A **concept** is a non-reserved `.md` file with a **non-empty `type`**
(§3.2). A `.md` without frontmatter or `type` (a `README.md`, a `SKILL.md`) is
not a concept: consumers skip it and the validator warns. Files and directories
starting with `.` are not part of the bundle. Everything else is soft guidance.
Consumers MUST tolerate missing optional fields, unknown types, unknown keys and
broken links, never reject a bundle over them.

## Conventions to apply

- **One concept = one file.** The file path (minus `.md`) is the concept ID.
- **Frontmatter:** `type` is required. Add `title`, `description`, `tags` when
  they aid consumption; add `resource` (a canonical URI) only for concepts bound
  to a real asset — omit it for abstract concepts.
- **Body:** prefer structural markdown (headings, tables, lists, fenced code).
  Conventional headings: `# Schema`, `# Examples`, `# Computation`.
- **Cross-links and path fields (§6):** a value starting with `/` resolves from
  the bundle root, any other value from the directory of its file. Both are
  valid, and the spec recommends neither (§13.2). This plugin's convention for
  **path fields** (`computation`, `executor.resource`, `attester.resource`,
  `superseded_by`, an in-bundle `resource` or `sources[].resource`) is the `/`
  form: it survives moving the file, and a bare value that a v0.2 bundle meant
  from the root changes meaning under v0.3. Percent-encode spaces. A link
  asserts an untyped relationship, its *kind* lives in the surrounding prose.
- **Extension keys (§4.1):** allowed at any level. Name your own
  `x-<producer>-<name>` (that prefix is reserved for extensions), and keep keys
  you do not know when you edit a file.
- **Reserved files:** `index.md` (directory listing, no frontmatter, except the
  bundle-root index, which carries the bundle metadata of §8.1: `okf_version`
  (quoted), `title`, `description` (when an agent should pick this bundle),
  `license`, and this plugin's extension keys (§4.1):
  `x-okf-skills-upkeep: enforced` to arm the Stop hook, plus
  `x-okf-skills-recursive: true` (or a depth `n`: levels below the root, `true`
  is 6) to make the hook watch nested git repos. The older unprefixed `upkeep` /
  `recursive` still work but are deprecated, and `/okf:validate --migrate`
  renames them) and `log.md` (ISO-dated history, newest first, no
  frontmatter). Never use these names for concepts.
- **What goes in `log.md` (an okf-skills convention):** §9 only says a log
  records the history of changes. This plugin keeps it to lifecycle events, written in the bundle-root
  `log.md`: a bundle **created**, a concept **deprecated** or retired, one
  concept **superseding** another, concepts **regenerated** after their source
  changed, a **verification** pass. Routine edits to a concept do not get an
  entry: its `generated` and git already record them. A log is append-only, so
  never rewrite or drop an existing entry.

## The families (all optional, all worth filling)

- **Trust (§5.2):** `generated: { by, at }` — who produced the current content
  and when. `verified: [{ by, at }]` — who confirmed it since (a bare mapping is
  one entry, and both `by` and `at` are required). Write `by` in the **actor
  convention** (§7): `<producer>/<version>` for an agent, `human:<id>` for a
  person, `team:<id>` for a group, `process:<id>` for an automated job. Use
  `human:` whenever a person authored or signed off, consumers key trust tiers
  off that prefix (a `team:` sign-off is only machine-confirmed). A
  verification counts only when its `at` is at or after `generated.at` (§5.3):
  when you rewrite content, bump `generated.at` and leave older `verified`
  entries as history. The concept is no longer human-reviewed until a human
  confirms the new text.
- **Timestamps (§5):** a date-time with an offset (`"2026-06-30T14:00:00Z"`)
  or a date only (`"2026-06-30"`, start of that day UTC). Quote them. A
  date-time without an offset is invalid. Use the date-time form for
  `generated.at` and `verified[].at`.
- **Lifecycle (§5.4–5.5):** `status: draft|stable|deprecated` (absent means
  stable, any other value means not current), `superseded_by: /path/to/new.md`
  on a deprecated concept that has a replacement, and `stale_after`, an
  absolute instant, not a TTL. Stale means "check again", not "false". Omit
  `stale_after` when no review date is known. To **move or rename** a concept,
  leave a short deprecated concept at the old path with `superseded_by` set to
  the new one, so old links keep working.
- **Provenance (§5.1):** `sources: [{ id, resource, title, author,
  usage_count, last_modified }]` plus a `usage_window: { from, to }` sibling of
  `sources` framing every `usage_count` (an entry may carry its own to override
  it); a `usage_count` without a window warns. `resource` is required per entry
  and may be a URL, a bundle path, or a scope descriptor. Attribute a specific
  claim with a markdown footnote whose label is the source's `id`:
  `…sharded daily.[^ga4-schema]` plus a `[^ga4-schema]: …` definition. The label
  is the join key, it must match a `sources[].id`.
- **Attestation (§10):** a sanctioned computation is its own concept,
  `type: Attested Computation`, carrying `runtime` (required), `parameters`,
  `executor`, `attester`, and the computation itself under `# Computation` (or a
  `computation:` path). Concepts that need the value link to it. Never inline a
  number's SQL into the concept that narrates it.

**Reading an older bundle?** v0.1 superseded two constructs (Appendix B):
`timestamp` is now `generated.at`, and a body `# Citations` list is now
`sources`. A v0.2 bundle (or one declaring no version) may hold bare path
fields written from the bundle root: if one does not resolve from its file's
directory, try the root (§12.1). Read all of these, write v0.3, and when you
touch a legacy concept in **maintain** mode, fix it as part of the edit. The
validator warns on each, and `--migrate` rewrites a whole bundle.

Templates to copy: [concept](templates/concept.md), [index](templates/index.md),
[log](templates/log.md).

## Default bundle location

Use `.okf/` at the repository root unless the project already uses another
location. Commit it alongside the code it describes — knowledge as code.

## Modes

### produce — create or extend a bundle

**Starting a brand-new bundle?** Use the init fast-path instead of hand-writing
the first files — it scaffolds a conformant `index.md`, `log.md`, and a
`getting-started.md` concept with full recommended frontmatter in one shot:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_init.py" <target-dir> [--title "..."]
```

It refuses to touch a directory that already has `.md` files unless `--force`
is given. Then extend it:

1. Read [reference/SPEC.md](reference/SPEC.md).
2. Pick the source(s): **code** (derive concepts from source, READMEs,
   docstrings, config), **docs/wiki** (distill pages into concepts, record the
   originals in `sources`), **manual** (decisions, playbooks, metrics).
3. Choose a directory layout by domain (e.g. `services/`, `datasets/`,
   `decisions/`). One concept per file.
4. Write each concept from [templates/concept.md](templates/concept.md): set a
   descriptive `type`, fill recommended fields, record `generated` and the
   `sources` you actually read, cross-link related concepts.
5. Add/refresh `index.md` per directory (and `okf_version: "0.3"`, `title`,
   `description` in the root index frontmatter, which you keep intact when you
   regenerate the listing). A new bundle gets a dated **Creation** entry in `log.md`. Extending
   an existing one does not.
6. Validate (see below). Fix every error before finishing.

### maintain — keep a bundle in sync with reality
1. Identify which concepts the change affects (search by `resource`, path, or
   topic). This bookkeeping is exactly what agents are good at — touch every
   affected file in one pass.
2. Update the body and `generated.at` (with your own actor in `generated.by`);
   fix or add cross-links; create new concepts for new assets; mark removed
   assets `status: deprecated` (with `superseded_by` when something replaces
   them) and note the deprecation in `log.md` rather than
   silently deleting context. Facing a whole v0.1 or v0.2 bundle rather than a
   stray field? Do not hand-edit it, run the validator's `--migrate` once.
3. Update the relevant `index.md` files. Append a dated `log.md` entry only if
   the change is a lifecycle event (see *What goes in `log.md`*).
4. Validate.

### consume — use a bundle as context
1. Read the bundle-root `index.md` first for progressive disclosure (its
   `description` says when the bundle applies), then follow links only into the
   concepts relevant to the task.
2. Weigh what you read: `status: draft`/`deprecated` or an unknown status, a
   `stale_after` already past or unparseable, or no *current* `verified` event
   (one at or after `generated.at`) all mean "check before relying on this". A
   deprecated concept with `superseded_by`: follow it and use the replacement.
   Treat broken links as not-yet-written knowledge, not errors.
3. Need a number an `Attested Computation` covers? Run *its* computation with
   values bound to the declared `parameters` — never write your own query.
4. If you learn something durable while working, switch to **maintain** and
   write it back.

## Validation (do this before declaring done)

Never eyeball conformance — run the deterministic checker. Invoke the companion
**`validate`** skill (`/okf:validate <bundle-dir> --strict`), which ships the
checker. If that skill is not installed, run it directly:

```bash
uv run "${CLAUDE_SKILL_DIR}/../validate/scripts/okf_validate.py" <bundle-dir> --strict
```

Resolve every `ERROR` (hard §11.1 failures). Under `--strict` warnings also fail
the run (exit 1), so clear them too; drop `--strict` (or use `--max-warnings N`)
if you only want §11 conformance gated.
