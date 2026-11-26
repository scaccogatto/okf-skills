<!--
  OKF adoption snippet.

  This file is NOT loaded automatically. Paste the block below into the CLAUDE.md
  of a project that adopts OKF (or into ~/.claude/CLAUDE.md to apply it globally).
  It is what makes the soft-mode "consume / maintain" behavior actually happen.
  For enforced upkeep instead, set `x-okf-skills-upkeep: enforced` in
  .okf/index.md's frontmatter to activate the plugin's dormant Stop hook.
-->

## Open Knowledge Format (OKF)

This project keeps shared knowledge as an OKF bundle in `.okf/`.

- **Before a task**, if `.okf/` exists, read `.okf/index.md` first and follow
  links into the concepts relevant to the work. Weigh what you read: a `draft` or
  `deprecated` `status`, a `stale_after` already past, or no `verified` entry all
  mean "check before relying on this". Treat broken links as not-yet-written
  knowledge, not errors.
- **After a change** that affects a documented asset (service, API, schema,
  table, metric, policy, runbook, decision), update the matching concept: refresh its body and
  `generated: { by, at }`, and fix cross-links. Create a new concept for any new
  asset. By okf-skills convention (OKF §9 only asks for a history of changes),
  append a dated entry to the bundle-root `log.md` only for a lifecycle event:
  a concept created, deprecated, superseded, regenerated after its source
  changed, or verified. Routine edits get no log entry.
- **Trust is earned, not written.** Never add a `verified` event for content you
  generated. Never invent or infer a `human:<id>` (not from git config, not from
  the OS user): use `human:` only for a named person who wrote or confirmed the
  content and whom you were told about. Record yourself in `generated.by` as
  `<producer>/<version>`.
- **Capturing new knowledge** → use the `/okf-skills:okf` skill (modes: produce,
  maintain, consume).
- **Before committing** bundle changes → run `/okf-skills:validate .okf --strict` and
  resolve every error. Add `--lint` if this project also wants the okf-skills
  house style (missing `title`, `description`, `tags`, `generated`), which is
  optional and not spec.

Conformance rule to respect: every concept file needs YAML frontmatter with a
non-empty `type` (a `.md` without one is skipped as a non-concept). Everything
else is optional. The bundle targets OKF v0.3. If you meet a v0.1 concept (a
`timestamp` field or a `# Citations` section), migrate it to `generated.at` /
`sources` as part of the edit. OKF accepts both path forms, and the okf-skills
convention is to write in-bundle path fields with a leading `/`. Bump `generated.at` whenever you change content, so an older human review no
longer counts as current.
