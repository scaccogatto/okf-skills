<!--
  OKF adoption snippet.

  This file is NOT loaded automatically. Paste the block below into the CLAUDE.md
  of a project that adopts OKF (or into ~/.claude/CLAUDE.md to apply it globally).
  It is what makes the soft-mode "consume / maintain" behavior actually happen.
  For enforced upkeep instead, set `upkeep: enforced` in .okf/index.md's
  frontmatter to activate the plugin's dormant Stop hook.
-->

## Open Knowledge Format (OKF)

This project keeps shared knowledge as an OKF bundle in `.okf/`.

- **Before a task**, if `.okf/` exists, read `.okf/index.md` first and follow
  links into the concepts relevant to the work. Weigh what you read: a `draft` or
  `deprecated` `status`, a `stale_after` already past, or no `verified` entry all
  mean "check before relying on this". Treat broken links as not-yet-written
  knowledge, not errors.
- **After a change** that affects a documented asset (service, API, schema,
  metric, runbook, decision), update the matching concept: refresh its body and
  `generated: { by, at }`, fix cross-links, and append a dated entry to the
  nearest `log.md`. Create a new concept for any new asset.
- **Capturing new knowledge** → use the `/okf:okf` skill (modes: produce,
  maintain, consume).
- **Before committing** bundle changes → run `/okf:validate .okf --strict` and
  resolve every error.

Conformance rule to respect: every concept file needs YAML frontmatter with a
non-empty `type`. Everything else is optional. The bundle targets OKF v0.2 — if
you meet a v0.1 concept (a `timestamp` field or a `# Citations` section), migrate
it to `generated.at` / `sources` as part of the edit.
