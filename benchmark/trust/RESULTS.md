# Trust benchmark — results

Run against `PROTOCOL.md` revision 8, tagged as `trust-benchmark-prereg-rev8`
before the measurement run. 946 measurement trials, `claude-opus-5`, 2026-09-02.
Analysis by the committed `analyze.py`; every number below is reproducible from
the published rows.

## Headline

**The primary result is invalid under the protocol's own rule, and the effect it
would have reported is at the ceiling.**

- The pre-registered undefined-cell rule (§3.2) invalidates the primary contrast
  when more than 10% of items have zero committed answers in a primary arm.
  **16.3% do** (7 of 43: one in A1, six in B1). §3.2 says such a result is
  *declared invalid, not adjusted*, and that is what this is.
- The number it would have reported, for the record: A1's conditional stale rate
  is **97.7pp below** B1's, 95% CI [93.0, 100.0]. Under the §3.4 worst case,
  where every A1 `neither` is counted as a wrong answer, **93.7pp** [85.0, 98.3].
- The invalidation and the size of the effect have the same cause: the control
  arm does not answer. Where the treatment reads the frontmatter, the control
  says `unknown`.

**A ceiling effect is not a strong result, it is a sign the experiment was built
around what it was measuring.** Read §"What this does not show" before quoting
any number here.

## What was measured

| Arm | Trials | stale | fresh | neither | Conditional stale rate |
|---|---|---|---|---|---|
| B0 — stripped, no instruction | 172 | 112 | **0** | 60 | 100.0% |
| B1 — stripped, operational instruction | 301 | 178 | **0** | 123 | 100.0% |
| A0 — full frontmatter, no instruction | 172 | **0** | 161 | 11 | 0.0% |
| A1 — full frontmatter, field semantics | 301 | **0** | 282 | 19 | 0.0% |

The separation is total. Across 473 control trials the consumer asserted the
current value **zero times**; across 473 treatment trials it asserted the
superseded value **zero times**. There is no overlap to compute a subtler
statistic on.

Three secondary readings matter more than the headline number:

1. **The instruction alone does nothing.** B1 − B0 is **0.0pp**. Telling a
   consumer "do not assert superseded facts; always prefer the most current
   information", with no metadata to act on, changed its answers not at all.
   This is what the B1 arm existed to detect (§5), and it detected it.
2. **The metadata alone does everything.** A0 − B0 is **−97.7pp**: the
   frontmatter without any instruction about how to read it produces the same
   result as the frontmatter plus the §5.3–§5.5 semantics. The model applied
   `status: deprecated`, `stale_after` and `verified` unprompted.
3. **The two arms fail differently.** Of B1's 123 `neither`, **116 are the
   literal token `unknown`**: the control detects the conflict and declines. Of
   A1's 19 `neither`, **none are `unknown`** — they are answers that assert the
   current value in a phrasing the grader does not accept ("By a collector
   restart — the stream set is configuration…"). The treatment's residual error
   is grading, the control's is refusal.

Per shape, conditional stale rate, B1 → A1:

| Shape | Items | B1 | A1 |
|---|---|---|---|
| limit-changed | 13 | 100.0% | 0.0% |
| reversed-recommendation | 14 | 100.0% | 0.0% |
| default-flipped | 6 | 100.0% | 0.0% |
| renamed-identifier | 6 | 100.0% | 0.0% |
| removed-capability | 3 | 100.0% | 0.0% |
| changed-precedence | 1 | 100.0% | 0.0% |

The shape counts are the survivors of §7 selection, not the corpus: 86 candidates
were calibrated and 43 survived. Survival is very uneven — limit-changed 12/14,
changed-precedence 1/12 — so the item set is dominated by two shapes and the
per-shape rows for the other four rest on a handful of items each.

## Pre-registered criteria, one by one

| Criterion | Result |
|---|---|
| §3.2 undefined-cell ceiling (≤10% of items) | **16.3% — invalidates the primary result** |
| §3.3 `neither` cap (A1 ≤ B1 + 10pp) | holds: A1 6.3%, B1 40.9% |
| §3.5 minimum effect (15pp) | 97.7pp |
| §3.7 CI excludes zero | yes, [93.0, 100.0] |
| §3.4 worst-case sensitivity | 93.7pp [85.0, 98.3] |
| §3.2 B1-side exclusion (6 items) | −97.3pp [91.9, 100.0] |

The B1-side exclusion is the one §3.2 demanded be published alongside, because
imputing a refusing control as fully stale inflates the contrast in favour of the
hypothesis. Excluding those six items changes the estimate by 0.4pp: the
inflation is real and it is not where the effect comes from.

## What this does not show

The protocol committed (§12) to putting this in the headline rather than the
footnotes, and after three corpus iterations it is more true than when it was
written.

- **The control has no recency channel by construction, and the corpus was
  rebuilt twice to make sure of it.** The first corpus let the control win
  outright: replacements announced their own recency in prose and shared a
  filename convention, and a control trial said so in as many words — *"every
  `*-notes.md` file is an update layer reporting current state"*. Corpus v2
  removed those channels. So B1 cannot obey its own instruction even in
  principle, and A1 − B1 is a **mechanism demonstration**: the consumer uses the
  channel when the channel exists, and has nothing else to use when it does not.
- **It is not an estimate of what trust metadata is worth in a real corpus**,
  where prose, filenames, dates in the text and repository history all carry
  recency signal — as this corpus's own first draft demonstrated by accident.
- **Items were selected for trapping the control** (§7: raw B0 stale rate ≥50%
  in calibration). Half the calibrated candidates were discarded because the
  control did *not* reliably assert the superseded value on them. The 100%
  control failure rate is therefore partly selection, and the honest
  interpretation of "100% → 0%" is *"on items where the control was already
  known to fail, the metadata converts every failure"*, not *"the control fails
  everywhere"*.
- **One model, one family, synthetic corpus.** The §12 replication on a second
  model family was not run.

## What it does show

Given all of that, one claim survives the scoping, and it is the claim §2 made:

> A consumer reading a bundle with v0.2 lifecycle and trust frontmatter does not
> assert facts that the frontmatter marks superseded, and the same consumer
> reading the same prose without that frontmatter cannot tell which fact is
> current — and, told to prefer current information, still cannot.

The mechanism works, and the instruction is not what makes it work. On this
corpus the fields carry the whole effect and the wording carries none of it.

## The measurement's own defects, recorded

§13's package is only worth something if it includes what went wrong.

1. **A second model was inside the consumer.** The first measurement attempt's
   records showed an `advisor_message` iteration served by `claude-fable-5`: this
   machine enables an advisor and `--safe-mode` does not disable it (72 of 320
   calibration rows, 8 of 10 probe trials). Fixed at rev 8, the 19 affected rows
   discarded, verified absent from all 946 published rows.
2. **The isolation claim in rev 6 was false.** Asked to quote what preceded its
   prompt, a trial read back a SessionStart hook's persona instruction and the
   maintainer's global `CLAUDE.md`. 192 calibration trials were discarded.
3. **The corpus leaked recency twice** (above), costing a second 192-trial
   calibration.
4. **The committed analysis script had the effect sign inverted.** §3.7's floor
   is a floor on the *reduction*, and the code compared the signed contrast
   `A1 − B1` against +15pp, so a perfect result would have been reported as a
   failure. Corrected at rev 9 with tests for both directions, after the run and
   with the result already invalid under §3.2 — so the correction could not
   change this verdict, and it is recorded here rather than quietly applied.
5. **Calibration was not re-run after defect 1.** Calibration selects items and
   never enters a result (§7), so the advisor makes the selection noisier rather
   than the comparison wrong. A deliberate cost decision, stated rather than
   left to be inferred.

## Reproducing

    uv run benchmark/trust/run.py --phase calibration --backend cli --jobs 8
    uv run benchmark/trust/power.py benchmark/trust/runs/calibration/B0.jsonl
    uv run benchmark/trust/run.py --phase measurement --backend cli --jobs 8
    cat benchmark/trust/runs/measurement/*.jsonl > /tmp/all.jsonl
    uv run benchmark/trust/analyze.py /tmp/all.jsonl

Published with this file: the 86-candidate corpus, the harness, the grader and
its adversarial tests, the analysis, and every measurement trial with its
session id, resolved model, usage and full invocation
(`benchmark/trust/runs/measurement/`). Calibration rows are published too, marked
as what §7 discards.

Cost of the published measurement: $100.14 over 946 trials. Total spend across
the discarded runs, the three calibrations and the probes: roughly $310.
