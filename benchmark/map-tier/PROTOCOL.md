# Map-phase routing: analyzer tier and dispatch shape

An engineering A/B, written before the measurement run and committed with it. It is
not a pre-registered experiment in the sense of `benchmark/trust/` or `benchmark/gate/`:
one run per arm, one repository, no confidence intervals. Its job is to decide two
configuration questions for the backfill skill, not to publish an effect size.

## Questions

1. **Tier.** The map phase is a bulk read: the analyzer moves evidence (a capped diff or
   a session turn) into a fixed structure and never judges the bundle. Does routing it to
   the cheap tier (`haiku`) degrade the analyses compared with the current default
   (`sonnet`), when the weaver stays on `sonnet` at high effort?
2. **Dispatch.** One analyzer call per event pays the agent overhead (system prompt,
   instructions, round trip) on every event, including a session turn that needs one
   `jq` call and one write. Does grouping small events eight per call degrade the
   analyses (cross-event contamination, missing files), at either tier?

## Subject

This repository at `85db7fd`, extracted once from `main` with the skill's own extractor:

    okf_backfill_events.py <repo> --skip-globs "benchmark/*/runs/**" \
        --skip-globs "docs/self.html" --skip-globs "docs/assets/**"

208 events, 147 live (76 git, 71 session turns), 2026-06-14 to 2026-09-03. The three
skip globs are the choice a user of this repository would make: trial data and the
generated visualisation carry no decision content. The same `events.jsonl` feeds every
arm; the emitter runs with the same globs.

"Small" event: a session turn, or a git commit whose numstat totals at most 60 changed
lines. 103 small events form 13 chronological batches of 8; the 44 large commits are
always dispatched alone.

## Arms

| Arm | Analyzer model | Effort | Dispatch | Analyzer calls |
|---|---|---|---|---|
| A | sonnet | medium | solo | 147 |
| B | haiku | medium | solo | 147 |
| C | sonnet | medium | batched | 57 |
| D | haiku | medium | batched | 57 |

Constant across arms: the analyzer instructions (`agents/event-analyzer.md` at this
commit, body used verbatim as the prompt, ids dispatched and events fetched by the agent),
the capped diff emitter with default caps (300 diff lines, 120 per file, 400 chars per
line), the weaver (`agents/bundle-weaver.md`, `sonnet`, effort high, batches of 25
analyses, one sequential chain per arm), and the finalize step (indices, coverage check,
validator, anti-degeneration greps). Analyzer calls from all arms share one pool of 10
concurrent agents, interleaved round-robin, because both earlier benchmarks lost runs to
high concurrency.

Model names are the tier names the agent frontmatter resolves to on the host at run
time; the results file records the run date.

## Metrics

Primary, per event, deterministic (`metrics.py`, paired across arms on event id):

- **missing**: live events with no analysis file.
- **template_ok**: frontmatter has the four fields, the four sections are exactly the
  template's, no line outside a bullet or header (preamble, commentary, restated diff).
- **violation_rate**: candidate concept names that are not kebab-case or are derived from
  a change type or a placeholder, over all candidates (the same rules finalize greps for).
- **entity_precision** (git events): path-like entities that belong to the event's own
  numstat, over all path-like entities. This doubles as the contamination check for
  batched arms: an entity from a sibling event in the batch is a miss.
- **truncated_agree**: the analysis' `truncated` flag equals the emitter's declared value
  for that commit (ground truth computed by running the emitter once per live commit).
  Measures whether the worker read the summary line at all.
- **bytes**, **candidates_n**, **rationale_over2_rate**: size and discipline of the output.

Secondary, per arm, smoke only: coverage check exit code, validator exit code, concept
count, log bullet count, anti-degeneration greps. One weaver run per arm leaves weaver
variance unmeasured, so bundle-level differences between arms are not attributed.

Judgment layer: a paired spot-read of ten analyses (five large commits, five session
turns) across A and B, looking for a wrong claim, a fabricated rationale, or an entity
the evidence does not contain.

## Decision rules (fixed before the run)

`haiku` ships as the analyzer default if, against arm A:

- missing analyses do not exceed A's by more than 2;
- violation_rate does not exceed A's by more than 0.05;
- entity_precision is not below A's by more than 0.10;
- template_ok_rate is at least 0.90 and truncated_agree_rate is at least 0.90;
- coverage and validator pass for arm B after finalize;
- the spot-read finds no systematic failure (more than one of the ten pairs).

Batching ships (as the documented dispatch rule) if, at the tier that ships, the batched
arm meets the same thresholds against its solo counterpart and its entity_precision on
batched events is not below the solo arm's by more than 0.10.

If a rule fails, the configuration stays as it is and the failure is reported as such.

## Limits, declared

One repository with a short history, one run per arm, one host and model family, the
author's own repository as subject. The emitter and the output contract were introduced in
the same change and are held constant, so this measures the tier and the dispatch shape
on top of them, not against the previous raw `git show` reading.
