---
type: Tool
title: okf_backfill_events.py
description: Deterministic event extractor and capped diff emitter for the backfill skill.
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/backfill/scripts/okf_backfill_events.py
tags: [python, backfill, uv]
status: stable
generated: { by: human:scaccogatto, at: "2026-09-21T00:00:00Z" }
---

# Overview

Turns `git log --first-parent --numstat` commits and Claude session transcripts
(`~/.claude/projects/<slug>/*.jsonl`) into `events.jsonl`, one event per line,
sorted by timestamp, byte-identical for the same repo. Each event carries a `skip`
field (optional) marking low-signal events — lockfile-only commits, merge-only
commits, slash-command chatter — determined by explicit, unit-tested rules.

# Diff emitter

The `--show <sha>` flag reads the whole first-parent diff for a commit and emits
a deterministic sample: complete stat, patches capped per file (default 120 lines)
and total (default 300 lines), cut at hunk or file boundaries with a marker, generated
files' patches omitted, over-long lines shortened (default 400 chars), and a fixed
last line declaring `truncated=true` or `truncated=false`. `--only <path>` is the
one permitted follow-up to narrow the diff.

# Used by

- [backfill skill](/skills/backfill.md): drives extraction and capped diffs during map phase
- Analyzers in `agents/`: fetch event JSON with `jq`, read git evidence only via the emitter

# Tests

Unit tests live in `tests/test_okf_backfill_events.py`.
