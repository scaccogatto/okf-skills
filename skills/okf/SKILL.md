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
[reference/SPEC.md](reference/SPEC.md). It is the verbatim OKF v0.1 specification
and the source of truth for every rule below.

## The one hard rule

A bundle is conformant (§9) iff: every non-reserved `.md` file has a parseable
YAML frontmatter block, and every such block has a **non-empty `type`** field.
Everything else is soft guidance. Consumers MUST tolerate missing optional
fields, unknown types, and broken links — never reject a bundle over them.

## Conventions to apply

- **One concept = one file.** The file path (minus `.md`) is the concept ID.
- **Frontmatter:** `type` is required. Add `title`, `description`, `tags`,
  `timestamp` (ISO 8601) when they aid consumption; add `resource` (a canonical
  URI) only for concepts bound to a real asset — omit it for abstract concepts.
- **Body:** prefer structural markdown (headings, tables, lists, fenced code).
  Conventional headings: `# Schema`, `# Examples`, `# Citations`.
- **Cross-links:** standard markdown links; prefer absolute bundle-relative
  form (`/services/auth-api.md`). A link asserts a relationship; its *kind* lives
  in the surrounding prose, not the link.
- **Reserved files:** `index.md` (directory listing, no frontmatter — except the
  bundle-root index may carry only `okf_version`) and `log.md` (ISO-dated change
  history, newest first). Never use these names for concepts.

Templates to copy: [concept](templates/concept.md), [index](templates/index.md),
[log](templates/log.md).

## Default bundle location

Use `.okf/` at the repository root unless the project already uses another
location. Commit it alongside the code it describes — knowledge as code.

## Modes

### produce — create or extend a bundle
1. Read [reference/SPEC.md](reference/SPEC.md).
2. Pick the source(s): **code** (derive concepts from source, READMEs,
   docstrings, config), **docs/wiki** (distill pages into concepts, link the
   originals under `# Citations`), **manual** (decisions, playbooks, metrics).
3. Choose a directory layout by domain (e.g. `services/`, `datasets/`,
   `decisions/`). One concept per file.
4. Write each concept from [templates/concept.md](templates/concept.md): set a
   descriptive `type`, fill recommended fields, cross-link related concepts.
5. Add/refresh `index.md` per directory (and `okf_version: "0.1"` in the root
   index). Append a dated entry to `log.md`.
6. Validate (see below). Fix every error before finishing.

### maintain — keep a bundle in sync with reality
1. Identify which concepts the change affects (search by `resource`, path, or
   topic). This bookkeeping is exactly what agents are good at — touch every
   affected file in one pass.
2. Update the body and `timestamp`; fix or add cross-links; create new concepts
   for new assets; mark removed assets (`**Deprecation**`) rather than silently
   deleting context.
3. Update the relevant `index.md` files and append a dated `log.md` entry
   describing what changed.
4. Validate.

### consume — use a bundle as context
1. Read the bundle-root `index.md` first for progressive disclosure, then follow
   links only into the concepts relevant to the task.
2. Treat broken links as not-yet-written knowledge, not errors.
3. If you learn something durable while working, switch to **maintain** and
   write it back.

## Validation (do this before declaring done)

Never eyeball conformance — run the deterministic checker. Invoke the companion
**`validate`** skill (`/okf:validate <bundle-dir> --strict`), which ships the
checker. If that skill is not installed, run it directly:

```bash
uv run "${CLAUDE_SKILL_DIR}/../validate/scripts/okf_validate.py" <bundle-dir> --strict
```

Resolve every `ERROR` (hard §9 failures). Warnings are soft; fix them when cheap,
but they never block.
