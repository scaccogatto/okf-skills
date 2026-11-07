#!/bin/bash
# OKF Stop hook - dormant by default.
# Fires only when BOTH hold:
#   1. the repo's bundle opts in: `upkeep: enforced` in .okf/index.md frontmatter
#   2. the user has not opted out: OKF_HOOK != "off"
# Optional: `recursive: true` in the same frontmatter makes the hook find nested git
# repos by itself and count their uncommitted tracked changes too.
input=$(cat)
# loop guard in plain grep, no jq: if this line cannot run, the hook re-blocks forever
printf '%s' "$input" | grep -q '"stop_hook_active"[[:space:]]*:[[:space:]]*true' && exit 0
[ "$OKF_HOOK" = "off" ] && exit 0
[ -f .okf/index.md ] || exit 0
# a flag must sit inside the frontmatter (between the first two --- lines)
frontmatter_has() {
  awk -v re="^$1[[:space:]]*\$" '/^---[[:space:]]*$/{n++;next} n==1 && $0 ~ re{f=1} END{exit !f}' .okf/index.md
}
frontmatter_has 'upkeep:[[:space:]]*enforced' || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
# count only changes to tracked files: an untracked path is not yet a documented
# asset, and treating it as one made the hook false-fire on tooling dirs (.claude/,
# .venv/, ...). New-asset authoring is the maintain flow's job, not this backstop's.
# The two Claude Code settings files are left out too (#58): `/plugin` writes
# .claude/settings.json, which no concept documents, and blocked every Stop until
# committed. Every other path under .claude/ (commands, hooks, skills) still counts.
tracked_changes() {
  git -C "$1" status --porcelain 2>/dev/null | grep -v '^??' \
    | grep -vE '^.. \.claude/settings(\.local)?\.json$'
}
# anything under .okf/ already touched, untracked included (a new concept starts
# untracked) -> assume the bundle was maintained. Not log.md alone: it records
# lifecycle events only, so most maintained changes never touch it.
[ -n "$(git status --porcelain -- .okf 2>/dev/null)" ] && exit 0
block() {
  where=""
  if [ -n "$1" ]; then
    nested=$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')
    where=" (including changes in nested repos: $nested)"
  fi
  cat <<JSON
{"decision":"block","reason":"This repo's .okf/ bundle declares \`upkeep: enforced\` and there are uncommitted changes$where, but nothing under .okf/ changed. If a documented asset changed, update the matching concept (body + generated); add a dated log.md entry only for a lifecycle event (creation, deprecation, supersession, regeneration, verification). If no documented asset changed, you may finish."}
JSON
  exit 0
}
# the outer repo is dirty: block now, no need to look for nested repos
[ -n "$(tracked_changes .)" ] && block ""
# nested-repo discovery is opt-in: `recursive: true` in the same frontmatter
# `recursive: true` means depth 6, `recursive: <n>` (positive integer) means depth n;
# any other value leaves discovery off
recursive=$(awk '/^---[[:space:]]*$/{n++;next} n==1 && /^recursive:[[:space:]]*(true|[1-9][0-9]*)[[:space:]]*$/{v=$0; sub(/^recursive:[[:space:]]*/, "", v); sub(/[[:space:]]*$/, "", v); print v; exit}' .okf/index.md)
[ -n "$recursive" ] || exit 0
depth=$recursive
[ "$depth" = "true" ] && depth=6
# A separate git repo checked out inside the project (usually gitignored by the
# outer one) is invisible to the outer status, so find them. The hook timeout is
# 15 s and a naive find took over 13 s on a monorepo with dozens of nested
# worktrees; pruning heavy dirs keeps it under 0.5 s. Pruned: .git, Claude Code
# worktrees (.claude/worktrees), dependency and build output (node_modules, .venv,
# venv, target, dist, build, .next, .turbo, .nx, __pycache__). Depth counts the
# directory levels below the project root that a nested repo's own directory may sit
# at: `app` is 1, `repos/app` is 2, `repos/app/inner` is 3. So its .git is searched
# up to depth + 1 (no -mindepth: it would also disable the prunes above at depth 1;
# ./.git, the only depth 1 hit, is pruned already).
# Known gaps: symlinked nested repos are not followed; a nested repo whose own
# directory is named like a pruned one (build, dist, target, ...) is not found;
# only the literal lowercase `recursive: true` enables discovery.
# Fail open: a repo that cannot be inspected is skipped.
# A .git found is skipped when it is:
#   1. a linked worktree of the outer repo (same common git dir): a separate
#      checkout, usually an agent or parallel session with its own hook, which the
#      hook deliberately ignores
#   2. a submodule: the outer status already sees its pointer change
#   3. a linked worktree of a repo that lives inside the project: ignored for the
#      same reason as 1 (linked worktrees of repos OUTSIDE the project still count)
#   4. a repo with its own .okf/ bundle, touched or not: its own enforced hook covers it
root=$(pwd -P)
realdir() { (cd "$1" 2>/dev/null && pwd -P); }
outer_common=$(realdir "$(git rev-parse --git-common-dir 2>/dev/null)")
[ -n "$outer_common" ] || exit 0
# the loop prints the dirty repos, one per line, and is captured: a pipeline
# subshell cannot hand variables back
dirty=$(find . -maxdepth $((depth + 1)) \( -path ./.git -o -path '*/.claude/worktrees' -o -name node_modules -o -name .venv -o -name venv -o -name target -o -name dist -o -name build -o -name .next -o -name .turbo -o -name .nx -o -name __pycache__ \) -prune \
  -o -name .git -print -prune 2>/dev/null | sort |
while IFS= read -r g; do
  d=${g%/.git}
  common=$(cd "$d" 2>/dev/null && realdir "$(git rev-parse --git-common-dir 2>/dev/null)") || continue
  [ -n "$common" ] || continue
  [ "$common" = "$outer_common" ] && continue
  [ -n "$(git -C "$d" rev-parse --show-superproject-working-tree 2>/dev/null)" ] && continue
  gitdir=$(cd "$d" 2>/dev/null && realdir "$(git rev-parse --git-dir 2>/dev/null)") || continue
  if [ "$gitdir" != "$common" ]; then case "$common/" in "$root"/*) continue;; esac; fi
  [ -d "$d/.okf" ] && continue
  [ -n "$(tracked_changes "$d")" ] && printf '%s\n' "${d#./}"
done)
[ -n "$dirty" ] || exit 0
block "$(printf '%s\n' "$dirty" | awk 'NR>1{printf ", "} {printf "%s", $0}')"
