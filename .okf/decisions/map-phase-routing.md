---
type: Decision
title: Route the backfill map phase like a bulk read
description: Cap what the analyzer reads in the script layer, dispatch small events in batches, keep judgment on the weaver's tier, and measure the analyzer tier instead of assuming it.
tags: [adr, backfill, routing, cost, benchmark]
status: stable
generated: { by: claude/fable-5.1, at: "2026-09-05T18:00:00Z" }
sources:
  - id: map-tier-protocol
    resource: https://github.com/scaccogatto/okf-skills/blob/main/benchmark/map-tier/PROTOCOL.md
    title: Map-phase routing A/B protocol
    last_modified: 2026-09-05
  - id: map-tier-results
    resource: https://github.com/scaccogatto/okf-skills/blob/main/benchmark/map-tier/RESULTS.md
    title: Map-phase routing A/B results
    last_modified: 2026-09-05
  - id: spotify-portal
    resource: https://engineering.atspotify.com/
    title: Spotify Engineering, "Portal by Spotify cut my Claude Code token usage by 90%", 3 September 2026
    last_modified: 2026-09-03
---

# Context

Spotify published a routing pattern for coding agents: a hook intercepts the expensive model
before it opens a large file and hands the read to a cheap worker that returns structured
bullets only; scripts build the request so the agent never handles the transport; skills stay
advisory; editing, reasoning and anything small are never delegated; and the bill is the
point. Their numbers (90% saved on bulk reads, a 350-line threshold, 10 to 30 seconds per
delegation) are one author's on one Java monorepo, by their own footnote. The patterns
travel; the numbers do not.

The [backfill skill](/skills/backfill.md) already had that boundary: the map phase is a bulk
read (evidence into a fixed structure) and the reduce phase is the judgment (naming, update
over create, log intent). What it lacked was enforcement of what the bulk reader sees. The
analyzer ran a raw `git show`, and the harness cuts long tool output blindly: mid-hunk,
character-based, at a threshold that differs by host and build. A cheap worker does not
notice a cut it was never told about. The coverage gate cannot see it either: coverage means
every event is mapped, not that every event was read.

# Decision

1. **The script reads everything and decides what the model sees.** `okf_backfill_events.py
   --show <sha>` reads the whole first-parent diff and emits a deterministic sample: the
   complete stat (entities survive any cap), patches capped per file and cut at hunk or
   file boundaries, generated files' patches dropped even in mixed commits, over-long lines
   shortened (one generated file in this repository has a 61,537-character line that
   numstat counts as "1+1"), and a fixed last line that declares `truncated=true|false`.
   `--only <path>` is the one permitted follow-up. This is script-layer determinism, not a
   hook: nothing blocks a raw `git show`. A hook stays deferred, as in
   [dormant hooks](/decisions/dormant-hooks.md): here the failure a block would prevent is
   recoverable rework caught by finalize's deterministic greps and coverage check, not an
   unrecoverable expensive read, so the post-hoc gate buys most of what a pre-hoc block would.
2. **Counts travel, content does not.** The orchestrator dispatches event ids and reads
   `wc`, `jq -r .id` and `ls`; analyzers fetch their own events, write bullets-only analyses
   with a `truncated` flag, and reply one line per event; the weaver replies counts.
3. **Small events are dispatched in batches.** A session turn or a commit of at most 60
   changed lines is small; small events go eight per analyzer call, large commits alone.
   Measured: 57 calls instead of 147, a third off the map phase at the same tier, no loss on
   any per-event metric and no cross-event contamination.
4. **The analyzer tier is measured, not assumed.** Two runs of the pre-registered rules
   found that `haiku` extracts claims, entities and rationale from commits at parity with
   `sonnet`, and that both of its failures were contract failures a cheap worker makes with
   an under-specified instruction: it copied the last summary line it saw, and it filled
   thin session evidence with the plausible continuation. Both instructions are now explicit
   in the analyzer file, whatever tier runs it. Run 3, with both sentences in place, passed
   every pre-set rule, the truncation flag at the threshold (0.905 against 0.90): `haiku` is
   the analyzer default, batched, at about 30 dollars per full backfill of this history
   against 46; the agent file is the place to retier.
5. **Judgment stays on the judgment tier.** The weaver runs on `sonnet` at high effort in
   every configuration; its frontmatter contract now asks for `YYYY-MM-DD` in
   `sources[].last_modified`, because every arm's `--strict` run failed on that warning.

Rejected or deferred: a PreToolUse hook for the analyzer (deferred, above); temperature as a
knob (the agent frontmatter does not expose it, `effort` is the knob); zero-residue
delegation (Spotify keeps nothing; the backfill keeps its analyses for audit and resume, on
purpose); the "64 analyzers concurrently" cost note (both earlier benchmarks lost runs to
high concurrency; waves of 4 to 8, and a pool of 10 held for 436 agents).

# Consequences

The reduce phase costs as much as a `sonnet` map (about 21 dollars per arm on this history,
at assumed list prices) in every configuration, because the weaver re-reads a growing context
across about 90 tool turns per batch of 25 analyses. The next cost lever is the weaver's
context shape, not the analyzer tier. The cheap tier saved 45% on the map, not 80%: it needed
more than twice the API calls for the same events.

The two sentences the cheap tier needed are the durable lesson: a resolved prompt is what
makes a cheap executor work, and "resolved" is discovered by measuring, one failure at a time.
