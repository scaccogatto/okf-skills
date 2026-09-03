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
{"id":"git:<sha>","source":"git","ts":"<ISO8601 Z>","sha":"...","author":"...","subject":"...","body":"...","files":[{"path":"...","add":N,"del":N}]}
{"id":"session:<file>:<lineno>","source":"session","ts":"<ISO8601 Z>","user":"...","outcome":"...","title":"...","branch":"...","skip":"..."}
```

- **Git events** come from `git log --first-parent --numstat`.
- **Session events** pair each user message with the **last** assistant text
  block of that turn (the wrap-up), extracted from
  `~/.claude/projects/<repo-slug>/*.jsonl` and worktree subdirs.
- **Timestamps** are normalized to UTC ISO 8601 strings ending in `Z`.
- **Skip field** (optional, added by extraction): marks low-signal events —
  see §3, never overridden by replay.

## 2. Protocol: Preflight → Extract → Bootstrap → Replay (Map+Reduce) → Finalize

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

### Replay: two-phase map/reduce protocol

The replay is now structured in two phases to enforce semantic depth and anti-degeneration rules:

#### Phase 1: Map (parallel analysis, per-event)

Launch one `okf:event-analyzer` agent per live event (those without `skip` field), orchestrated
in waves via Claude Code's Workflow `agentType` parameter. Each analyzer:
- Reads the event (git diff or session transcript)
- Outputs `analyses/<event-id>.md` (event id with `:` sanitized to `-`) to scratchpad
- Never touches `.okf/`
- Is resumable: skip events already in `analyses/`

**Host-agnostic fallback** (if no Workflow support): spawn generic subagents with the same
system prompt as `agents/event-analyzer.md`, one per event, collecting analyses to scratchpad.

#### Phase 2: Reduce (sequential folding, one agent)

Run a single `okf:bundle-weaver` agent that:
- Reads all analyses in chronological order
- Folds them into `.okf/`, updating or creating concepts
- Enforces anti-degeneration rules (§3)
- Updates `log.md` with dated bullets (the "why" from each analysis)
- Manages cursor (`.okf/.backfill-state.json`) for resume capability
- Is the only actor that writes `.okf/`

**Resume behavior:** both phases support resumption. Phase 1 skips already-analyzed event ids;
Phase 2 restarts from `last_id` in the cursor.

### Domain priming (advisory)

Before starting the map phase, read the repository's README and directory structure to sketch
a candidate taxonomy of concepts (skills, integrations, decisions, etc.). This priming is
*advisory only* — it helps the analyzer emit better candidate names. The *guarantee* that
no events are lost comes from the deterministic coverage check in Finalize (§5), not from
priming; analyses without candidate names still flow to the weaver.

### Finalize: validate and clean up

1. **Write `index.md` per directory by hand** (do NOT run `okf_init.py` — it
   would scaffold placeholder files): one `# Section` per directory, one
   bullet per concept, `* [Title](file.md) - description` taken from each
   concept's frontmatter (SPEC §8). The root `index.md` keeps its
   `okf_version: "0.2"` frontmatter and links every subdirectory.

2. **Add final log entry** (today's date, appended to existing dated section if present):
   ```
   ## 2026-09-01

   - **Backfill**: reconstructed from N events by okf-backfill/0.9.2
   ```

3. **Delete cursor:**
   ```bash
   rm -f .okf/.backfill-state.json
   ```

4. **Run self-checks for anti-degeneration rules:**
   ```bash
   # No concept filenames derived from change type
   ! find .okf -name "*.md" | grep -E "merge-pull-request|(^|/)(feat|fix|chore|docs)[:-]"
   
   # No non-kebab-case characters in filenames
   ! find .okf -name "*.md" | grep -E "[^a-z0-9/.-]"
   
   # No identical consecutive log bullets
   awk 'p==$0 && /^- / {exit 1} {p=$0}' .okf/log.md
   ```

5. **Run coverage check to guarantee every event is mapped:**
   ```bash
   uv run "${CLAUDE_SKILL_DIR}/scripts/okf_backfill_events.py" \
     --check-coverage events.jsonl .okf
   ```
   Exit code 0 means all live events (non-skipped) appear in the bundle's `sources` or log.
   Exit code 1 with a list of unmapped ids means the weaver skipped some events; fix and re-run.

6. **Validate bundle schema:**
   ```bash
   uv run "${CLAUDE_SKILL_DIR}/../validate/scripts/okf_validate.py" .okf --strict
   ```
   Fix every error before finishing.

7. **Report** the resulting bundle:
   - Concept count per directory
   - Log entry samples (first and last)
   - Coverage check result (all events mapped)
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

## 4. Anti-degeneration rules

The analyzer and weaver enforce these rules to prevent the bundle from devolving into
a mechanical listing of commits or a taxonomy-by-accident:

1. **Concept names describe domain entities, not changes.** Forbidden:
   - Filenames derived from git subject: `merge-pull-request-#2-....md`, `feat:-add-docs-skill.md`, `fix:-handle-edge-case.md`
   - Bare action words: `update.md`, `fix.md`, `add-feature.md`
   - Non-kebab-case: spaces, underscores, capitals, special characters (allowed: `[a-z0-9-]` only)

   Example: a commit with subject "feat: add presales pipeline" touches a domain concept.
   The *concept* is named `presales-pipeline.md` (the entity), not `feat:-add-presales-pipeline.md`
   (the change). The change history lives in frontmatter `sources` and log bullets.

2. **Prefer update over create.** Every event is analyzed for which concepts it touches; if
   a concept already exists and the analysis fits, update its `sources` and body. Only create
   a new concept if the analysis reveals a distinct domain entity not yet captured.

3. **Log bullets explain intent, not restate subjects.** A bullet should answer "why did this
   change happen?" from the commit body or session outcome, never just re-read the subject:
   - Bad: `- Added presales-pipeline.md feature`
   - Good: `- **Presales pipeline**: formalized the sales workflow to clarify handoff points`

4. **No identical consecutive bullets.** Group same-date updates by concept to avoid:
   ```
   - Feature X update
   - Feature X update
   - Feature X update
   ```
   Instead: one bullet per concept, or combine into "Feature X: multiple updates".

## 5. Implementation notes

- **Determinism**: extraction is byte-identical; replay is not (time, LLM variance).
  Both are auditable: events.jsonl is deterministic, map analyses are stored and resumable,
  reduce loop is human-readable and cursor-backed.
- **Privacy**: events.jsonl goes to scratchpad, never committed. Session turn text is
  truncated (head+tail) before extraction.
- **Cost note**: deep replay reads ~1 diff per git commit (full `git show` output) to
  extract rationale. For histories >500 events, consider splitting into sub-ranges and
  replaying sequentially, or use `--skip-globs` to exclude low-signal paths (e.g.,
  vendored dependencies, generated code). Map phase is massively parallel (64 analyzers
  can run concurrently); reduce is sequential but much cheaper (concepts already analyzed).
- **Future sources** (not implemented): GitHub PR/issue text, release notes, CI/deploy logs
  — all optional post-MVP. **Lore protocol** (arXiv 2603.15566): on repos that adopt git
  trailers (structured decision metadata), the extracted event's `body` already contains
  trailers in a machine-readable format. The analyzer and weaver should use trailers as
  the primary source of "why" (overriding generic inference from diff content).
- **Trust metadata**: `generated.by` is the backfill agent (`okf-backfill/0.9.2`), not
  claimed as human-reviewed (`human:...`); concepts are correctly `unverified` (SPEC §5.3).
  Map-phase analyses are working artifacts (stored for auditability during reduce); the
  weaver's output is the canonical bundle.

