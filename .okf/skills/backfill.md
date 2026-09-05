---
type: Skill
title: backfill skill
description: Reconstruct an OKF bundle from git history and session transcripts — event-sourcing for repos that predate this toolchain.
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/backfill/SKILL.md
tags: [skill, bundle-reconstruction, history, event-sourcing, deep-replay, routing]
status: stable
generated: { by: claude/fable-5.1, at: "2026-09-05T12:00:00Z" }
sources:
  - id: spec-§5.2
    resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/okf/reference/SPEC.md#52-trust-generated-and-verified
    title: OKF v0.2 spec §5.2 Trust metadata
  - id: map-tier-protocol
    resource: https://github.com/scaccogatto/okf-skills/blob/main/benchmark/map-tier/PROTOCOL.md
    title: Map-phase routing A/B protocol
---

# Overview

Replays a repository's decision history — git commits and Claude session
transcripts — to reconstruct its OKF bundle as if the [stop hook](/components/stop-hook.md)
had been active from the start. Extracts events deterministically (same repo →
byte-identical stream); replays via LLM interpretation with drift-aware metadata.

The skill bridges the gap for repos created before OKF adoption: instead of
starting with an empty bundle, it captures the actual narrative of what was
decided, why, and when.

# Protocol

1. **Preflight**: check if bundle can be rebuilt (fresh or resume from cursor).
2. **Extract**: generate a deterministic event stream (events.jsonl) from git and
   sessions.
3. **Bootstrap** (fresh only): initialize `.okf/index.md` and `log.md`.
4. **Replay** (two-phase):
   - **Map** (parallel, waves of 4 to 8): `agents/event-analyzer.md` receives event
     ids (never content), fetches each event with `jq`, reads commit evidence only
     through the capped diff emitter, and writes `analyses/<event-id>.md`; its
     reply is one line of counts per event.
   - **Reduce** (sequential): `agents/bundle-weaver.md` folds analyses into the
     bundle in chronological order, enforcing anti-degeneration rules and managing
     cursor state; its reply is one line of counts.
5. **Finalize**: generate directory indices, validate, check coverage, report
   agents per phase and truncated analyses, and clean up.

# Key behaviors

- **Deterministic extraction**: git (first-parent, reverse, numstat) and session
  turn pairing (user → last assistant text of the turn) produce byte-identical
  events.jsonl.
- **Skip rules**: three kinds of events are marked as low-signal and skipped during
  replay — lockfile-only commits, merge-only commits, slash-command chatter.
  Rules are explicit and unit-tested; no LLM discretion over what counts.
- **Capped diff emitter** (`--show <sha>`): analyzers never run a raw `git show`.
  The extractor reads the whole first-parent diff and emits a deterministic sample:
  complete stat, patches capped per file and cut at hunk or file boundaries with a
  marker at every cut, generated files' patches dropped even in mixed commits,
  over-long lines shortened, and a fixed last line declaring `truncated=true|false`
  that the analyzer copies into its frontmatter. `--only <path>` is the one permitted
  follow-up. The harness cuts long tool output blindly and host-dependently; the
  emitter moves that decision into the script layer, where it is deterministic,
  domain-aware and declared. Defaults: 300 diff lines, 120 per file, 400 chars per
  line.
- **Routing boundary**: the map phase is a bulk read (evidence into a fixed
  structure) and the reduce phase is the judgment (naming, update over create, log
  intent). The analyzer's tier lives in its frontmatter (`model`, `effort`); forking
  the agent file retiers the map phase without touching the skill. The tier itself
  is measured, not assumed: see the [map-tier protocol](/skills/backfill.md#sources).
- **Context hygiene**: the orchestrator handles ids and counts only (`wc`, `jq -r .id`,
  `ls | wc`). Events, analyses and diffs never enter its context; agents return
  counts, never content.
- **Deep semantic replay**: Map phase analyzes each event's content (capped diff,
  session outcome) to extract rationale and domain entities; reduce phase
  folds analyses into the bundle. Together they enable deep understanding of
  *why* changes were made, not just mechanical change listing.
- **Anti-degeneration rules**: concepts are named for domain entities
  (e.g., `presales-pipeline.md`), never for change types or commit subjects.
  Log bullets explain intent, not restate subjects. Rules are enforced by the
  weaver and validated in finalize.
- **Coverage guarantee**: deterministic `--check-coverage` verifies every live
  event appears in the bundle's `sources` or log before declaring the backfill
  complete. Unmapped events cause finalize to fail. Coverage means mapped, not
  fully read: the truncated-analysis count in the final report covers the gap.
- **Concurrency**: waves of 4 to 8 analyzers. Both earlier benchmarks lost runs to
  high-concurrency mass failures ([gate results](/decisions/trust-benchmark.md));
  the skill no longer claims 64-way parallelism.
- **Trust metadata**: concepts inherit `generated.by: okf-backfill/0.9.3` (not
  claimed as human-reviewed); they are correctly `unverified` under §5.3. Each
  commit becomes a source with its timestamp.
- **Privacy**: events.jsonl is scratchpad-only, never committed. Session turn
  text is truncated (head+tail) before extraction. Map-phase analyses are
  working artifacts, retained for auditability during reduce (a deliberate
  divergence from zero-residue delegation: replayability is the point).

# Usage

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_backfill_events.py" <repo-dir>
  [--out events.jsonl] [--no-sessions] [--sessions-dir ~/.claude/projects]
  [--max-text 2000] [--skip-globs GLOB ...]

uv run "${CLAUDE_SKILL_DIR}/scripts/okf_backfill_events.py" <repo-dir> --show <sha>
  [--only <path>] [--max-diff-lines 300] [--per-file-lines 120] [--max-line-chars 400]

/okf:backfill <repo-dir> [--no-sessions]
```

The extractor runs standalone; the skill drives it and the replay loop per the
[replay protocol](/skills/backfill.md).

# Design rationale

Event-sourcing preserves the *sequence* of decisions, not just the current state:
the log.md can narrate why a concept exists in its current form. Deterministic
extraction + auditable replay = a reconstructed bundle that is both replayable
and trustworthy, even though the LLM interpretation has variance.

Routing follows the same principle one level down: only what carries judgment is
billed at the judgment tier, and everything the model reads in bulk is shaped by a
script that read all of it first.
