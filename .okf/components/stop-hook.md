---
type: Tool
title: okf-stop-check.sh
description: Dormant Stop hook — a no-op unless a bundle opts in to enforced upkeep.
resource: https://github.com/scaccogatto/okf-skills/blob/main/hooks/okf-stop-check.sh
tags: [bash, hook, enforcement]
status: stable
generated: { by: "agent:claude-fable-5", at: "2026-08-02T12:18:55Z" }
---

# Overview

The plugin's only hook, registered via `hooks/hooks.json` on the `Stop` event.
Ships with every install but is **dormant by default** — see the
[dormant hooks decision](/decisions/dormant-hooks.md) for why it exists and
what it replaces.

# The gate

`hooks/okf-stop-check.sh` exits 0 (no-op) unless *every* one of these holds,
checked in order:

1. it is not itself running inside a stop-hook loop (`stop_hook_active`).
2. the user has not opted out: env `OKF_HOOK` is not `off`.
3. `.okf/index.md` exists in the working tree.
4. that file's **frontmatter** — between the first two `---` lines — contains
   the literal line `upkeep: enforced`, the opt-in flag a bundle sets to ask
   for enforcement. A mention elsewhere in the file does not count.
5. the working tree is a git repo with **modified tracked files** — untracked
   paths are ignored, since a brand-new file is not yet a documented asset.
   (This is what keeps tooling dirs like `.claude/` or `.venv/` from
   false-firing the hook.)
6. `.okf/log.md` is not already among those changes (if it is, the bundle was
   plausibly maintained this session, so the hook stays quiet).

Only when all six hold does it block, asking the agent to update the matching
concept and append a dated `log.md` entry before finishing.

# Activation

A bundle turns this on by adding `upkeep: enforced` to `.okf/index.md`'s
frontmatter. A user force-disables it regardless of bundle settings by
setting `OKF_HOOK=off` in their environment.

# Known limits

* Gate 5 counts any *tracked* modification, not just this session's — a tree
  left dirty by earlier work triggers the nudge too; the block reason tells
  the agent it may finish if no documented asset changed. The flip side of
  ignoring untracked files: if the only change is a new untracked file that
  ought to get a concept, the hook stays quiet — authoring new assets is the
  maintain flow's job, not this backstop's.
* Conversely, an uncommitted `.okf/log.md` left over from an earlier session
  satisfies gate 6 and silences the hook until it is committed.
* Paths resolve from the session's working directory: a bundle not at
  `./.okf/` (monorepo subdirectory, session launched elsewhere) is never seen.
* The loop guard greps the raw JSON for `"stop_hook_active": true` rather
  than parsing it — deliberate, so a missing `jq` can never disable the guard
  and re-block forever.
