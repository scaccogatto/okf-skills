---
type: Tool
title: okf-stop-check.sh
description: Dormant Stop hook — a no-op unless a bundle opts in to enforced upkeep.
resource: https://github.com/scaccogatto/okf-skills/blob/main/hooks/okf-stop-check.sh
tags: [bash, hook, enforcement]
status: stable
generated: { by: "agent:claude-opus-5-5", at: "2026-10-19T00:00:00Z" }
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
   false-firing the hook.) The two Claude Code settings files,
   `.claude/settings.json` and `.claude/settings.local.json`, are ignored even
   when tracked: `/plugin` writes the first, and no concept documents it.
   Every other tracked path under `.claude/` (commands, hooks, skills) counts.
6. nothing under `.okf/` is changed, untracked files included (a new concept
   starts untracked). Any bundle change means it was plausibly maintained this
   session, so the hook stays quiet.

If the outer repo has tracked changes the hook blocks at once. Only otherwise,
and only when the frontmatter also carries `recursive: true` (or a positive
integer depth), does it look for
nested repos (see [Activation](#activation)); their tracked changes count by
the same rule as gate 5.

It blocks when gates 1 to 4 hold and either the outer repo or (with
`recursive: true`) a nested repo has tracked changes while nothing under `.okf/`
changed, asking the agent to update the matching
concept before finishing, and to add a `log.md` entry only for a lifecycle
event.

# Why not `log.md`

Until 0.10.0 gate 6 looked for `.okf/log.md` alone, which made every change
append a log entry. With parallel branches that turned the top of `log.md` into
a conflict on every merge (issue #54, from a project merging about ten PRs a
day). Upstream reads `log.md` as a rare, curated record of lifecycle events
(its sample bundle has four entries in five months), and an open upstream
proposal would make root `log.md` entries normative for supersession. So the
log stopped being the proof of upkeep, and any change under `.okf/` is.

The gates are covered by `tests/test_okf_stop_hook.py`, which runs the script
against throwaway git repos.

# Activation

A bundle turns this on by adding `upkeep: enforced` to `.okf/index.md`'s
frontmatter. A user force-disables it regardless of bundle settings by
setting `OKF_HOOK=off` in their environment.

A bundle that documents separate git repos checked out *inside* the project
(say `repos/app/`, each its own repo, gitignored by the outer one) adds
`recursive: true` to the same frontmatter: its own line, between the first two
`---` lines, next to `upkeep: enforced`. The value is `true` (depth 6) or a
positive integer `n` (depth n); anything else (`false`, `0`, `yes`, `True`, a
quoted value) leaves discovery off. The hook then finds nested repos by
itself, with no list to maintain, and counts their tracked changes like the
outer repo's. When nested repos contribute changes, the block reason names them
(paths relative to the project root). Without the key nothing changes. It is
read only when `upkeep: enforced` is set, and the validator allows it in the
root index.

Order matters for cost: the bundle-touched check runs first, then the outer
repo's own changes (which block without any discovery), and only then the
`recursive` flag and the `find`.

Discovery runs `find` for `.git` entries. Depth counts the directory levels below
the project root at which a nested repo's own directory may sit: `app` is 1,
`repos/app` is 2, `repos/app/inner` is 3 (nested repos inside nested repos are
found). The search goes to depth + 1 for the `.git` entry. The hook timeout is 15 s and an unpruned `find` took
over 13 s on a monorepo with dozens of nested worktrees; pruning `.git`,
`.claude/worktrees`, `node_modules`, `.venv`, `venv`, `target`, `dist`, `build`,
`.next`, `.turbo`, `.nx` and `__pycache__` brings it under 0.5 s. A hit is
skipped when it is:

* a linked worktree of the outer repo (same common git dir): a separate checkout,
  usually an agent or parallel session with its own hook, deliberately ignored;
* a submodule: the outer status already sees its pointer change;
* a linked worktree of a repo that lives inside the project: ignored for the
  same reason (linked worktrees of repos *outside* the project still count);
* a repo with its own `.okf/` directory, touched or not: its own enforced hook
  covers it.

A repo that cannot be inspected is skipped (fail open).

Known gaps: symlinked nested repos are not followed; a nested repo whose own
directory is named like a pruned one (`build`, `dist`, `target`, ...) is not
found; only the literal lowercase `recursive: true` enables discovery.

# The CI mirror

The hook only reaches people running the plugin. A contributor sending a PR from
a plain checkout gets nothing from it, so the same two obligations are enforced
again in `ci.yml`'s `version-bump` job, on the PR diff rather than on the working
tree: a PR touching `skills/*/scripts/**` or `hooks/**` must also touch `.okf/`,
and a PR that bumps the plugin version must add the matching `## [version]`
heading to `CHANGELOG.md`. Both share the job's `skip-version-check` label as the
bypass, and both live as steps inside that job rather than as new jobs, so the
set of required status checks does not change.

# Known limits

* Gate 5 counts any *tracked* modification, not just this session's — a tree
  left dirty by earlier work triggers the nudge too; the block reason tells
  the agent it may finish if no documented asset changed. The flip side of
  ignoring untracked files: if the only change is a new untracked file that
  ought to get a concept, the hook stays quiet — authoring new assets is the
  maintain flow's job, not this backstop's.
* Conversely, any uncommitted change under `.okf/` left over from an earlier
  session satisfies gate 6 and silences the hook until it is committed. So does
  touching an unrelated concept: the gate checks that the bundle moved, not
  that the right concept did.
* Discovery only sees repos whose directory sits within the configured depth (default 6) and outside the pruned directories. Committed changes in a nested repo are not seen, same as in the outer repo:
  only uncommitted tracked modifications count.
* Paths resolve from the session's working directory: a bundle not at
  `./.okf/` (monorepo subdirectory, session launched elsewhere) is never seen.
* The loop guard greps the raw JSON for `"stop_hook_active": true` rather
  than parsing it — deliberate, so a missing `jq` can never disable the guard
  and re-block forever.
