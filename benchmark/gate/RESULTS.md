# Write-side gate versus read-side metadata — results

Run against `PROTOCOL.md` revision 1, tagged `gate-benchmark-prereg-rev1` before
the measurement. 200 end-to-end pipelines (400 model calls) and 299 corpus-state
trials, `claude-opus-5`, 2026-09-02/03. Every number is reproducible from the
published rows.

## Headline

**Both mechanisms work, at sizes this experiment cannot tell apart. Neither makes
the other redundant.**

| Contrast | Reduction in stale rate | 95% CI | Verdict |
|---|---|---|---|
| **Write side** — gate vs no gate, end to end | **39.0pp** | [21.0, 58.0] | pass |
| **Read side, nobody acted** — expired `stale_after` vs unmarked | **28.0pp** | [14.0, 43.0] | pass |
| **Read side, someone acted** — `deprecated` vs unmarked | **35.0pp** | [20.0, 51.0] | pass |

Compared directly on the same 20 items, paired:

| Difference | Point | 95% CI |
|---|---|---|
| write side − read side (expired) | +11.0pp | [−10.0, +33.0] |
| write side − read side (marked) | +4.0pp | [−16.0, +25.0] |

Both intervals contain zero. §2's claim — *a gate reduces stale assertions at
least as much as read-side metadata* — is **not falsified**, and that is the
weakest true statement available: the gate is not measurably better either. At
n = 20 items the experiment separates each mechanism from doing nothing, and does
not separate the mechanisms from each other.

## The underlying rates

| Condition | Stale | Refusal |
|---|---|---|
| End to end, no gate | 48% | 3% |
| End to end, gate | 9% | 3% |
| Documentation stale, unmarked | 62% | 17% |
| Documentation stale, expired `stale_after` | 34% | 2% |
| Documentation stale, `deprecated` | 27% | 0% |
| Documentation synced (sanity control) | 0% | 0% |

Three things in that table matter more than the headline.

**1. Ungated writers leave the documentation alone 57% of the time.** With the
`AGENTS.md` gate the writer touched the documentation in 100 runs out of 100;
without it, 43 out of 100. That gap is the gate's entire mechanism, and it is
also the exact population where read-side metadata would act: the two are
complementary rather than competing, because the metadata only matters in the
cases where the writer did nothing, and that is more than half of them.

**2. Syncing is not the same as syncing correctly.** The gated arm touched the
documentation every single time and still produced a stale assertion in 9% of
pipelines. A process gate buys attention, not correctness.

**3. Marking a document `deprecated` leaves 27% of answers stale — where #40
measured 0%.** The difference is what the superseded document is competing
against. In #40 it was a replacement document; here it is a configuration file
stating the current value. A consumer that reads `status: deprecated` on a
document *still* prefers that document's prose to the config in a quarter of
trials. If that generalises, it is a caution about deprecating documentation
rather than deleting or rewriting it.

## What this answers, and what it does not

It answers #40's §14 in the direction of "neither, both": on this evidence a
write-side gate does not make read-side trust metadata redundant, and read-side
metadata does not make a gate pointless. The FastEndpoints pattern — a gate, no
`stale_after` — is defensible on these numbers, and so is the opposite.

**It cannot answer the question that actually separates them.** A per-trial
harness measures whether an agent obeys an explicit gate *once*. It says nothing
about six months of deadlines, a contributor who has not read `AGENTS.md`, or a
gate that quietly stops being enforced — which is exactly the failure mode
pre-set metadata is immune to, since a date expires whether or not anyone is
paying attention. Gated compliance here was 100/100. In a real repository that
number is a process question, not a model question, and this harness cannot see
it.

Further limits, declared: one model and one family; a synthetic repository with
one configuration file and one document, where a real one has hundreds and the
writer's attention is divided; an agent writer rather than a human; and items
inherited from #40, which selected them for trapping a consumer — the absolute
rates are not population estimates.

## What the probes got wrong, and why they still earned their cost

Two probes ran before the protocol was frozen, and their data is excluded from
every number above (§6).

- The writer probe estimated spontaneous documentation syncing at **5 of 6**. At
  scale it is **43 of 100**. A six-run probe was enough to scope the design and
  nowhere near enough to estimate the quantity, and the protocol's decision to
  keep probe data out of the result is the only reason that misestimate cost
  nothing but a sentence in this section.
- Both probes found defects in the harness itself: the document the writer met
  carried a `deprecated` status inherited from #40's corpus, and substring
  grading credited untouched documents as synced because `f_old` legitimately
  survives in a correctly updated document. The second defect is why the
  pipeline is closed with a real consumer instead of a file-level grader.

One defect the probes did not prevent: the consumer stage lost 260 of 299 runs
to the same high-concurrency mass failure #40 hit, and this runner had no resume,
so the partial batch was unrecoverable. Resume added, batch re-run at
concurrency 4, and the lost runs were never paid for twice.

## Reproducing

    uv run benchmark/gate/pipeline.py --stage endtoend --items 20 --reps 5 --jobs 4 \
        --out benchmark/gate/runs/endtoend.jsonl
    uv run benchmark/gate/pipeline.py --stage consumer --items 20 --reps 5 --jobs 4 \
        --states stale_unmarked,stale_expired,stale_marked \
        --out benchmark/gate/runs/states.jsonl
    uv run benchmark/gate/analyze.py --endtoend benchmark/gate/runs/endtoend.jsonl \
        --states benchmark/gate/runs/states.jsonl

Cost: $94.93 in total — $55.93 end to end, $33.17 for the corpus states, $5.83
for the probes.
