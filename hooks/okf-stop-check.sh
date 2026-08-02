#!/bin/bash
# OKF Stop hook - dormant by default.
# Fires only when BOTH hold:
#   1. the repo's bundle opts in: `upkeep: enforced` in .okf/index.md frontmatter
#   2. the user has not opted out: OKF_HOOK != "off"
input=$(cat)
printf '%s' "$input" | jq -e '.stop_hook_active == true' >/dev/null 2>&1 && exit 0
[ "$OKF_HOOK" = "off" ] && exit 0
[ -f .okf/index.md ] || exit 0
grep -q '^upkeep: enforced' .okf/index.md || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
changes=$(git status --porcelain 2>/dev/null)
[ -n "$changes" ] || exit 0
# log.md already touched this session -> assume the bundle was maintained
printf '%s\n' "$changes" | grep -q '\.okf/log\.md' && exit 0
cat <<'JSON'
{"decision":"block","reason":"This repo's .okf/ bundle declares `upkeep: enforced` and there are uncommitted changes, but .okf/log.md was not updated. If a documented asset changed, update the matching concept (body + generated) and append a dated log.md entry. If no documented asset changed, you may finish."}
JSON
