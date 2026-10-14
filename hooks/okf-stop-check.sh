#!/bin/bash
# OKF Stop hook - dormant by default.
# Fires only when BOTH hold:
#   1. the repo's bundle opts in: `upkeep: enforced` in .okf/index.md frontmatter
#   2. the user has not opted out: OKF_HOOK != "off"
# Optional: `upkeep_repos: <glob>` or `[<glob>, ...]` in the same frontmatter names
# nested git repos (relative to the project root) whose changes count too.
input=$(cat)
# loop guard in plain grep, no jq: if this line cannot run, the hook re-blocks forever
printf '%s' "$input" | grep -q '"stop_hook_active"[[:space:]]*:[[:space:]]*true' && exit 0
[ "$OKF_HOOK" = "off" ] && exit 0
[ -f .okf/index.md ] || exit 0
# the flag must sit inside the frontmatter (between the first two --- lines)
awk '/^---[[:space:]]*$/{n++;next} n==1 && /^upkeep:[[:space:]]*enforced[[:space:]]*$/{f=1} END{exit !f}' .okf/index.md || exit 0
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
changes=$(tracked_changes .)
# Nested repos the bundle documents: a separate git repo checked out inside the
# project (usually gitignored by the outer one) is invisible to the outer status.
# Globs come from `upkeep_repos` in the frontmatter, a single value or a flow list.
patterns=$(awk '/^---[[:space:]]*$/{n++;next}
  n==1 && /^upkeep_repos:/ {
    sub(/^upkeep_repos:[[:space:]]*/, ""); gsub(/[][\047"]/, "")
    k = split($0, a, ",")
    for (i = 1; i <= k; i++) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", a[i]); if (a[i] != "") print a[i] }
  }' .okf/index.md)
nested=""
default_ifs=$IFS
while IFS= read -r pattern; do
  IFS=   # expand the glob without splitting paths on spaces
  for dir in $pattern; do
    dir=${dir%/}
    [ -d "$dir" ] || continue
    [ "$(git -C "$dir" rev-parse --is-inside-work-tree 2>/dev/null)" = "true" ] || continue
    # the repo must be rooted at $dir, not a plain subdirectory of the outer one
    [ -z "$(git -C "$dir" rev-parse --show-cdup 2>/dev/null)" ] || continue
    nested_changes=$(tracked_changes "$dir")
    [ -n "$nested_changes" ] || continue
    changes="$changes
$nested_changes"
    nested="${nested:+$nested, }$dir"
  done
  IFS=$default_ifs
done <<PATTERNS
$patterns
PATTERNS
[ -n "$changes" ] || exit 0
# anything under .okf/ already touched, untracked included (a new concept starts
# untracked) -> assume the bundle was maintained. Not log.md alone: it records
# lifecycle events only, so most maintained changes never touch it.
[ -n "$(git status --porcelain -- .okf 2>/dev/null)" ] && exit 0
where=""
if [ -n "$nested" ]; then
  nested=${nested//\\/\\\\}
  nested=${nested//\"/\\\"}
  where=" (including changes in nested repos: $nested)"
fi
cat <<JSON
{"decision":"block","reason":"This repo's .okf/ bundle declares \`upkeep: enforced\` and there are uncommitted changes$where, but nothing under .okf/ changed. If a documented asset changed, update the matching concept (body + generated); add a dated log.md entry only for a lifecycle event (creation, deprecation, supersession, regeneration, verification). If no documented asset changed, you may finish."}
JSON
