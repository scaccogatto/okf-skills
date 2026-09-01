---
name: backfill
description: >-
  Reconstruct an OKF bundle by event-sourcing a repository's history (git log
  and Claude session transcripts). Use when creating an `.okf/` bundle for an
  existing repository that predates this skill, or when resuming an interrupted
  backfill session. Triggers on: "reconstruct the OKF bundle", "backfill the
  knowledge bundle", "event-source the history".
user-invocable: true
argument-hint: "[repo-dir] [--no-sessions] [--sessions-dir DIR]"
allowed-tools: Bash Read Write Edit
---

# Reconstruct an OKF bundle from history

This skill replays a repository's decision-making history (git commits and
Claude session transcripts) to rebuild its OKF knowledge bundle as if the
[okf](/okf) skill's Stop hook had been active from the start.

The extraction layer is **deterministic** (same repo → byte-identical events);
the replay layer is an LLM loop, **replayable and auditable but not
byte-identical** (timestamps, summaries change per run). See the event schema
(§1) and skip rules (§3).

## 1. Event schema

Git commits and session turns become events (JSONL, one per line, sorted by
timestamp then source):

```json
{"id":"git:<sha>","source":"git","ts":<epoch>,"sha":"...","author":"...","subject":"...","body":"...","files":[{"path":"...","add":N,"del":N}]}
{"id":"session:<file>:<lineno>","source":"session","ts":<epoch>,"user":"...","outcome":"...","title":"...","branch":"...","skip":"..."}
```

- **Git events** come from `git log --first-parent --numstat`.
- **Session events** pair user message → next assistant text, extracted from
  `~/.claude/projects/<repo-slug>/*.jsonl` and worktree subdirs.
- **Timestamps** are normalized to UTC epoch (floats).
- **Skip field** (optional, added by extraction): marks low-signal events —
  see §3, never overridden by replay.

## 2. Protocol: Preflight → Extract → Bootstrap → Replay → Finalize

### Preflight: check if bundle can be rebuilt

```bash
if [ -d <repo>/.okf ] && ! [ -f <repo>/.okf/.backfill-state.json ]; then
  echo "ERROR: .okf/ exists but is incomplete. Delete it to rebuild from scratch, or pass --resume to continue from the last checkpoint."
  exit 1
fi
```

If `.backfill-state.json` exists, resume from the cursor; otherwise, fresh bootstrap.

### Extract: generate event stream

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_backfill_events.py" <repo-dir> \
  --out events.jsonl \
  [--no-sessions] [--sessions-dir ~/.claude/projects] \
  [--max-text 2000] [--skip-globs "vendor/**"]
```

Write `events.jsonl` to the scratchpad (never committed). Report:
- Total events extracted, per-source counts, and per-rule skip counts.

### Bootstrap: initialize bundle (fresh only)

Create `.okf/` with:

```bash
mkdir -p <repo>/.okf
echo 'okf_version: "0.2"' > <repo>/.okf/index.md
echo '# Update Log' > <repo>/.okf/log.md
```

Cursor (`.okf/.backfill-state.json`):

```json
{"last_id": null, "done": 0}
```

### Replay: process events in order

Loop over consecutive chunks (~20 events) from `events.jsonl`, starting after cursor:

**Per event:**

1. Load cursor from `.backfill-state.json`.
2. If event `skip` field is set (§3 rule), advance cursor and continue.
3. **Else** (no skip): **mandatory** — create/update concepts and log entries
   - Interpret the event: what concepts does this git commit or session turn
     touch? Add/update `.okf/<domain>/<concept>.md` with frontmatter
     ```yaml
     type: <Inferred type>
     title: <Short title>
     description: <One-liner>
     tags: [<related tags>]
     generated:
       by: okf-backfill/0.1
       at: <ISO8601 now, replay time>
     sources:
       - id: git:<short-sha>  # For git events
         resource: "git:<full-sha>"
         last_modified: <event ts ISO8601>
     ```
   - Update `log.md`: prepend a dated section for the event's date (§9
     newest-first), group same-date events in one bullet list.
   - Cursor: increment `done`, update `last_id` to current event `id`, save
     `.backfill-state.json`.
4. Repeat until all events consumed or max chunk size reached.

**Cursor format** (`.okf/.backfill-state.json`):

```json
{"last_id": "git:abc123...", "done": 42}
```

On crash/resume, the loop restarts from `last_id`; events before it are skipped.

**Replay behavior:**

- One agent, streaming chunks.
- For large histories (>500 events), document how to split into sub-ranges
  and replay sequentially; no implementation required now.
- Concepts inherit repo structure: group by feature/service (`services/`,
  `datasets/`, `integrations/`, etc.); if unclear, use `concepts/`.
- Log prose: explain what changed and why (from commit message, session
  outcome), not just a machine restatement.

### Finalize: validate and clean up

1. **Generate `index.md` per directory:**
   ```bash
   uv run "${CLAUDE_SKILL_DIR}/../okf/scripts/okf_init.py" .okf --force --index-only
   ```

2. **Add final log entry** (today's date):
   ```
   ## 2026-09-01

   - **Backfill**: reconstructed from N events by okf-backfill/0.1
   ```

3. **Delete cursor:**
   ```bash
   rm -f .okf/.backfill-state.json
   ```

4. **Validate:**
   ```bash
   uv run "${CLAUDE_SKILL_DIR}/../validate/scripts/okf_validate.py" .okf --strict
   ```
   Fix every error before finishing.

5. **Report** the resulting bundle:
   - Concept count per directory
   - Log entry samples (first and last)
   - Validation result (pass/fail, warnings)

## 3. Skip rules

Events matching a rule below are marked `skip: <rule-id>` and skipped during
replay (cursor advances, no log entry):

| Rule | Condition | Rationale |
|------|-----------|-----------|
| `paths-only-generated` | Git commit touches ONLY lockfiles or generated code (vendor/, node_modules/, dist/, *.min.*, *.lock, etc.) | Noise: build byproducts, no knowledge content |
| `merge-no-files` | Git merge commit with no file changes (first-parent only) | Housekeeping |
| `session-command-noise` | Session user message is a slash command or <20 chars and has no useful outcome | Ephemeral UI/chatter |

Extend the first rule with `--skip-globs "extra/**"` for repo-specific patterns.

## 4. Implementation notes

- **Determinism**: extraction is byte-identical; replay is not (time, LLM
  variance). Both are auditable: events.jsonl is deterministic, replay loop
  is human-readable.
- **Privacy**: events.jsonl goes to scratchpad, never committed. Session turn
  text is truncated (head+tail) before extraction.
- **Future sources** (not implemented): GitHub PR/issue text, release notes,
  CI/deploy logs — all optional post-MVP.
- **Trust metadata** (§5.2): `generated.by` is the backfill agent
  (`okf-backfill/0.1`), not claimed as human-reviewed (`human:...`); concepts
  are correctly `unverified` (§5.3).

