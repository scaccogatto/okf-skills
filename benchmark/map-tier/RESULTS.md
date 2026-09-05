# Map-phase routing: results

Run against `PROTOCOL.md` as committed in `37ecf14`, on 2026-09-05. Subject: this repository
at `85db7fd`, 147 live events (76 commits, 71 session turns). One run per arm, no confidence
intervals: an engineering decision, not an effect size. Every number below comes from
`metrics.py` rows and the workflow's agent transcripts; the analyses, bundles and per-event
rows live in the session scratchpad and are not committed (they contain session text).

## Headline

**Batching ships. The cheap tier does not, on this evidence: it fails two of the six
pre-set rules, and both failures are about following the contract, not about reading the
diff.** On commits, `haiku` extracted claims, entities and rationale at parity with `sonnet`.
On the flag that says whether it saw a capped diff, and on session turns, it did what a
cheap worker does with an under-specified instruction: it took the last thing it saw.

| Rule (B, haiku solo, against A, sonnet solo) | Threshold | Measured | Verdict |
|---|---|---|---|
| missing analyses | at most A + 2 | 1 vs 2 | pass |
| violation_rate | at most A + 0.05 | 0.021 vs 0.034 | pass |
| entity_precision | at least A − 0.10 | 0.879 vs 0.862 | pass |
| template_ok_rate | at least 0.90 | 0.993 | pass |
| truncated_agree_rate | at least 0.90 | **0.787** (A: 0.987) | **fail** |
| coverage and validator, arm B | pass | coverage pass; validator 0 errors, `--strict` fails on warnings in every arm (see below) | pass, qualified |
| spot-read, ten paired analyses | at most one systematic failure | **three session turns overclaimed** (one invented action) | **fail** |

| Rule (C, sonnet batched, against A, sonnet solo) | Threshold | Measured | Verdict |
|---|---|---|---|
| missing analyses | at most A + 2 | 0 vs 2 | pass |
| violation_rate | at most A + 0.05 | 0.049 vs 0.034 | pass |
| entity_precision | at least A − 0.10 | 0.870 vs 0.862 | pass |
| entity_precision on batched events | at least A − 0.10 | 0.929 vs 0.901 | pass |
| template_ok_rate, truncated_agree_rate | at least 0.90 | 1.0, 0.961 | pass |
| coverage and validator, arm C | pass | coverage pass; validator 0 errors | pass, qualified |

## Run 1: the 2×2

| metric | A sonnet solo | B haiku solo | C sonnet batched | D haiku batched |
|---|---|---|---|---|
| analyzer calls | 147 | 147 | 57 | 57 |
| analyses present (of 147) | 145 | 146 | 147 | 146 |
| template_ok | 1.000 | 0.993 | 1.000 | 0.993 |
| violation_rate | 0.034 | 0.021 | 0.049 | 0.036 |
| entity_precision (git) | 0.862 | 0.879 | 0.870 | 0.941 |
| truncated_agree (git) | 0.987 | 0.787 | 0.961 | 0.853 |
| rationale_over2_rate | 0.000 | 0.164 | 0.020 | 0.137 |
| `[UNCLEAR]` used (analyses) | 47 | 1 | 19 | 6 |
| bytes per analysis | 1626 | 1634 | 1482 | 1438 |
| candidates per analysis | 2.43 | 2.93 | 2.22 | 2.49 |

Paired on the 144 events both A and B produced: entity precision B − A = +0.044 (B worse on
10 commits, better on 20, tied on 42); naming violations 12 (A) vs 9 (B); `truncated` flag
disagreements with the emitter 1 (A) vs 16 (B).

Paired on the 145 events both A and C produced: entity precision +0.009 (C worse on 18,
better on 12, tied on 43); violations 12 vs 16; flag disagreements 1 vs 3; C's analyses are
142 bytes shorter and carry 0.2 fewer candidates. No contamination signal: on the 103 small
events the batched arms group eight per call, C's entity precision is 0.929 against A's
0.901, and D's 0.994 against B's 0.815.

### What the flag failure is

All 16 of B's disagreements are the same shape: the emitter said `truncated=true`, the
analysis said `false`, and in every one of the 16 the agent had made the permitted `--only`
follow-up call. The follow-up prints its own summary line for one file, usually
`truncated=false`, and `haiku` copied that one. `sonnet` made the same follow-up on the same
commits and copied the first line. The instruction said "copies the emitter's last line",
which is ambiguous when there are two calls; the analyzer file now says "the last line of
the first `--show` call; a `--only` follow-up never changes it". Run 2 below measures the
flag again with that sentence in place.

### What the spot-read found

Five largest commits: both tiers produced accurate claims, entities from the commit's own
stat, and rationale from the commit body. `haiku`'s candidate names drift toward principles
(`test-corpus-signal-independence`, `model-refusal-path-specification`) where `sonnet` names
entities (`trust-benchmark-corpus-leakage`, `forced-answer-field-grading`); the weaver decides
names, so this is a quality of suggestion, not of the bundle. One `haiku` claim was not a
bullet (the 0.993), and it exceeded the two-bullet rationale cap in 16% of analyses against
0% for `sonnet`.

Five session turns: `haiku` wrote "then proceeds to merge the branch up-to-date with main"
for a turn whose outcome only records the intent to look at failing checks; wrote "User
conducted a critical evaluation" for a turn that only fetched the open items; and wrote
"critical review identified two distinct failure modes" for a one-word user turn. `sonnet`
reported the same three turns as intent or a first step and marked the missing why with
`[UNCLEAR]`. Across all analyses `sonnet` used `[UNCLEAR]` 47 times, `haiku` once. This is
the second contract failure: the cheap tier fills a gap in the evidence with the plausible
continuation unless told not to. The analyzer file now says so explicitly ("a session outcome
that only shows intent or a first step is reported as intent or a first step"); run 3 below
measures `haiku` with that sentence in place.

### Bundle level (smoke only; one weaver run per arm, variance unmeasured)

| arm | coverage | validator errors / warnings | concepts | log bullets |
|---|---|---|---|---|
| A sonnet solo | fail, 2 unmapped | 0 / 176 | 27 | 81 |
| B haiku solo | pass | 0 / 185 | 29 | 75 |
| C sonnet batched | pass | 0 / 119 | 35 | 80 |
| D haiku batched | fail, 4 unmapped | 0 / 365 | 33 | 86 |

A's two unmapped events are its two missing analyses (the map phase never wrote them; in the
skill's real flow the resume rule re-dispatches them). D's four are one missing analysis and
three events the weaver dropped in its second batch, where it also wrote the cursor with
unsanitized ids: weaver variance, the same `sonnet` weaver in every arm. `--strict` fails in
every arm for the same reason, warnings only: the weaver's frontmatter contract asked for an
ISO 8601 `last_modified` while the validator warns on anything finer than `YYYY-MM-DD`.
The weaver file now asks for the date. Zero errors in every arm; anti-degeneration greps
pass in every arm.

### Cost (run 1, estimated)

Token counts are summed from the agents' own usage records. Prices are assumed list prices per
million tokens (input 3.00 / output 15.00 / cache read 0.30 / cache write 3.75 for `sonnet`;
1.00 / 5.00 / 0.10 / 1.25 for `haiku`); the ratios matter more than the dollars.

| arm | map agents | map API calls | map est. USD | reduce est. USD | total est. USD |
|---|---|---|---|---|---|
| A sonnet solo | 147 | 749 | 23.28 | 21.98 | 45.93 |
| B haiku solo | 147 | 1684 | 12.87 | 21.39 | 34.90 |
| C sonnet batched | 57 | 526 | 15.36 | 21.27 | 37.43 |
| D haiku batched | 57 | 1209 | 8.96 | 20.18 | 29.68 |

Three things in that table matter more than the totals.

1. **Batching cut the map phase by a third at the same tier** (23.28 to 15.36) with no
   measurable quality cost. That is the agent overhead the infographic's "anything small"
   rule is about: a session turn needs one `jq` call and one write, and paid a full agent
   spawn for it.
2. **The cheap tier saved 45%, not 80%.** `haiku` needed 1684 API calls for the same 147
   events that `sonnet` did in 749: more tool turns per event, more context re-read per turn.
   A cheap worker that works less efficiently gives back part of its price advantage.
3. **The reduce phase costs as much as a `sonnet` map, in every arm.** The weaver folds 25
   analyses per invocation with a context that grows across ~90 tool turns, and 51M of its
   tokens are cache reads of that context. The next cost lever is the weaver's context shape
   (shorter batches, or a per-event fold that re-reads only the index), not the analyzer tier.

Wall clock for run 1: 115 minutes for 436 agents in a pool of 10, zero agent errors, zero
null results. The concurrency lesson from `benchmark/gate/RESULTS.md` held: 10 was fine.

## Run 2: the flag, with the clarified instruction

Arms A2 (sonnet solo) and B2 (haiku solo), same events, same emitter, the analyzer prompt of
run 1 plus one sentence: the flag copies the first `--show` call's last line and a `--only`
follow-up never changes it. 294 agents, 17 minutes, zero errors.

| metric | A2 sonnet solo | B2 haiku solo | (B, run 1) |
|---|---|---|---|
| analyses present (of 147) | 145 | 146 | 146 |
| template_ok | 0.986 | 1.000 | 0.993 |
| violation_rate | 0.046 | 0.027 | 0.021 |
| entity_precision (git) | 0.859 | 0.871 | 0.879 |
| truncated_agree (git) | 0.987 | **0.960** | 0.787 |
| rationale_over2_rate | 0.028 | 0.205 | 0.164 |
| `[UNCLEAR]` used | 40 | 1 | 1 |

Paired: B2's flag disagreements fell from 15 to 3 on the same 74 commits; every other
paired delta between B and B2 is within what sonnet shows between its own two runs
(A vs A2: violations 12 vs 16, entity precision +0.01, flag disagreements 1 vs 1). The flag
failure was the instruction, not the tier: the cheap worker copied the last summary line it
saw because the prompt said "the last line", and stopped once the prompt said which one.
Against A2, B2 passes every deterministic rule (missing 1 vs 2, violations 0.027 vs 0.046,
entity precision +0.012, template 1.0, flag 0.960). It still uses `[UNCLEAR]` once against
sonnet's 40, which is the run 3 question.

## Run 3: session turns, with the evidence-only instruction

Arm B3 (haiku solo), the analyzer prompt of run 2 plus one rule: the claim states what the
evidence shows happened; a session outcome that only shows intent or a first step is reported
as such; a missing why is `[UNCLEAR]`, not a guess. Compared against A2 (sonnet solo, run 2),
whose prompt lacks that sentence because sonnet already behaved that way. 147 agents, 10
minutes, zero errors, est. 13.41 USD.

| metric | A2 sonnet solo | B3 haiku solo | (B2) | (B) |
|---|---|---|---|---|
| analyses present (of 147) | 145 | 145 | 146 | 146 |
| template_ok | 0.986 | 0.986 | 1.000 | 0.993 |
| violation_rate | 0.046 | 0.025 | 0.027 | 0.021 |
| entity_precision (git) | 0.859 | 0.918 | 0.871 | 0.879 |
| truncated_agree (git) | 0.987 | 0.905 | 0.960 | 0.787 |
| rationale_over2_rate | 0.028 | 0.179 | 0.205 | 0.164 |
| `[UNCLEAR]` used | 40 | 4 | 1 | 1 |

Paired against A2 on 143 events: entity precision +0.061 (B3 worse on 8 commits, better on
24, tied on 41), naming violations 10 vs 13, flag disagreements 7 vs 1.

Spot-read, the same ten events as run 1. The invented action is gone: for the failing-checks
turn B3 now writes "then began investigating which checks are failing", for the fetch turn
"the assistant retrieved open PRs and issues as the foundation for this review", for the
one-word turn "resolved to apply two identified fixes". One borderline overclaim remains (a
drafting turn described as executed rather than begun), and one of B3's two missing analyses
fell in the sample (the v0.2 commit), which the deterministic rule already counts. `haiku`
still marks uncertainty four times where `sonnet` marks it forty: it stopped inventing, it
did not start flagging. Rationale runs past two bullets in 18% of its analyses.

Rules against A2: missing 2 vs 2, violations 0.025 vs 0.046, entity precision +0.059,
template 0.986, flag 0.905, spot-read one borderline case: **all pass**. The flag passes at
the edge: two `haiku` runs gave 0.960 and 0.905 where `sonnet` gives 0.987 twice, so about
one truncated commit in ten will reach the weaver unflagged; the finalize report puts the
flag count next to the deterministic estimate for exactly that reason.

## Decision

- **Analyzer default: `haiku`**, effort medium, with the two instructions that made it pass
  written into `agents/event-analyzer.md` (which summary line the flag copies; claims report
  intent as intent). Fork the file to retier. Measured against `sonnet` on this history:
  commits extracted at parity (entity precision higher, fewer naming violations), session
  turns reported as intent when the evidence stops at intent, the truncation flag at the
  threshold, map cost −43% solo (23.52 to 13.41) and −62% batched (23.28 to 8.96).
- **Dispatch: batched.** Session turns and commits of at most 60 changed lines go eight per
  call. −34% on the map at the same tier, no per-event loss, no contamination.
- **Weaver: `sonnet`, effort high**, unchanged; its `last_modified` contract now asks for a
  date. The reduce phase is the next cost lever, in any configuration.
- **Nothing was rejected by these rules.** Run 1's two failures were instruction failures,
  fixed in the prompt and re-measured; both fixes apply to any tier that runs the analyzer.

Shipping configuration on this history: about 30 USD per full backfill against 46 before
(run 1, arm D against arm A), with the reduce phase unchanged at about 21 of those 30.

## Limits, declared

One repository, one run per arm, one host and model family, the author's own history as
subject. The tier names resolved to `claude-sonnet-5` and `claude-haiku-4-5-20251001` on this
host. The judgment layer is one reader's paired read of ten analyses, chosen deterministically
(five largest commits, every fourteenth session turn), not a blinded panel. The prompt fixes
between runs were made after seeing run 1's failures, so runs 2 and 3 are follow-up
measurements of the same rules with a changed instruction, declared as such, not the
pre-registered run.
