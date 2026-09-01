---
type: Skill
title: backfill skill
description: Reconstruct an OKF bundle from git history and session transcripts — event-sourcing for repos that predate this toolchain.
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/backfill/SKILL.md
tags: [skill, bundle-reconstruction, history, event-sourcing]
status: stable
generated: { by: okf-backfill/0.1, at: "2026-09-01T00:00:00Z" }
sources:
  - id: spec-§5.2
    resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/okf/reference/SPEC.md#52-trust-generated-and-verified
    title: OKF v0.2 spec §5.2 Trust metadata
---

# Overview

Replays a repository's decision history — git commits and Claude session
transcripts — to reconstruct its OKF bundle as if the [stop hook](/components/stop-hook.md)
had been active from the start. Extracts events deterministicly (same repo →
byte-identical stream); replays via LLM interpretation with drift-aware metadata.

The skill bridges the gap for repos created before OKF adoption: instead of
starting with an empty bundle, it captures the actual narrative of what was
decided, why, and when.

# Protocol

1. **Preflight**: check if bundle can be rebuilt (fresh or resume from cursor).
2. **Extract**: generate a deterministic event stream (events.jsonl) from git and
   sessions.
3. **Bootstrap** (fresh only): initialize `.okf/index.md` and `log.md`.
4. **Replay**: loop over events, creating concepts and log entries; cursor
   checkpoints after each event (crash-safe resume).
5. **Finalize**: generate directory indices, validate, and clean up.

# Key behaviors

- **Deterministic extraction**: git (first-parent, reverse, numstat) and session
  turn pairing (user → next assistant text) produce byte-identical events.jsonl.
- **Skip rules**: four types of events are marked as low-signal and skipped during
  replay — lockfile-only commits, merge-only commits, slash-command chatter.
  Rules are explicit and unit-tested; no LLM discretion over what counts.
- **Trust metadata**: concepts inherit `generated.by: okf-backfill/0.1` (not
  claimed as human-reviewed); they are correctly `unverified` under §5.3. Each
  commit becomes a source with its timestamp.
- **Privacy**: events.jsonl is scratchpad-only, never committed. Session turn
  text is truncated (head+tail) before extraction.

# Usage

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_backfill_events.py" <repo-dir>
  [--out events.jsonl] [--no-sessions] [--sessions-dir ~/.claude/projects]
  [--max-text 2000]

/okf:backfill <repo-dir> [--no-sessions]
```

The extractor runs standalone; the skill drives it and the replay loop per the
[replay protocol](/skills/backfill.md).

# Design rationale

Event-sourcing preserves the *sequence* of decisions, not just the current state:
the log.md can narrate why a concept exists in its current form. Deterministic
extraction + auditable replay = a reconstructed bundle that is both replayable
and trustworthy, even though the LLM interpretation has variance.

