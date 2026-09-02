# Trust benchmark — protocol

**Status:** draft, revision 6. Revisions 1 through 5 were each corrected before
any run; §15 records the history.

**Spec under test:** OKF **v0.2**, as vendored at `skills/okf/reference/SPEC.md`,
okf-skills commit `c68f9f2` (2026-07-27). Every spec claim below is checkable
against that file at that commit.

## 1. Why this exists, and why it is not the benchmark that was removed

`benchmark/` was removed in #32 for a stated reason: it measured better answers,
cheaper reading and cross-session repetition cost. The spec claims none of those.
Word counts across the canonical SPEC: `token` 0, `cost` 0, `efficiency` 0,
`save/saving` 0, `repetition` 0.

Re-running that experiment with a better grader would repeat the same error more
rigorously. So this measures something the spec *does* claim, in its own words
(§1): knowledge that is readable, parseable, diffable, portable, and **above all
trustable**.

Trustability is also the one claim nobody has measured. The strongest published
OKF benchmark (`aws-samples/sample-okf-llm-wiki`, BIRD mini_dev, EX 74.0)
measures *sufficiency* — that a bundle carries enough structure for an agent to
work from — and measures it well. Trust is still untested by anyone.

## 2. The claim

**Claim.** The v0.2 lifecycle and trust fields — `status` (§5.4), `stale_after`
(§5.5), and the trust tier derived from `verified` (§5.3) — let a consumer avoid
asserting knowledge that has been superseded.

**Treatment is exactly the claim.** The superseded document carries `status:
deprecated`, a `stale_after` date in the past, and no `verified` entry; the
replacement carries a recent `verified` entry with a `human:` actor.

**No link from the superseded document to its replacement.** v0.2 defines no
supersession-pointer field: `status: deprecated` is *"kept for links and history;
no longer current"* (§5.4), which concerns inbound links surviving, not a
machine-readable successor. A link would do **navigation** work — redirecting the
agent to the right document — which is a different mechanism from a trust
judgment; including it would inflate the effect and make it unattributable.

If a supersession link would outperform the trust fields, that is a finding about
a **gap in the spec** and deserves its own experiment rather than being smuggled
into this one.

## 3. Pre-registered analysis and falsification

Fixed and committed before any run (§13).

### 3.1 Primary contrast

**A1 − B1, and only that one.** Revision 1 named "the metadata arm versus its
matched control", which left two candidate contrasts and therefore two chances to
succeed with no multiplicity correction. A0 − B0 and B1 − B0 are **descriptive
only** and carry no confirmatory weight.

### 3.2 Primary metric

**Conditional stale rate**, `stale / (stale + fresh)`: the share of *committed*
answers that are wrong. A raw stale rate can be driven down by an arm that simply
stops answering, and the instruction in A1 pushes in exactly that direction.

**Undefined-cell rule.** The conditional rate is undefined for an item with zero
committed answers in an arm, and by construction the arm where that happens is
A1. The default behaviour of any implementation would be to drop the item from
the pair — silently deleting the hardest items from the primary contrast, in
favour of the hypothesis. Pre-registered instead:

- an item with zero committed answers in a primary arm **stays in the contrast**,
  with its `neither` imputed as `stale` for that arm;
- the number of affected items is reported **per arm, never aggregated**;
- if affected items exceed **10%** of the item set, the primary result is
  declared **invalid**, not adjusted.

The per-arm split is not bookkeeping. The rule reads symmetrically, but its
effects are not: imputing on **A1** penalises the treatment, while imputing on
**B1** inflates the contrast *in favour of the hypothesis*. That case is rare —
B1 has no push toward refusal — but the path exists, so: if any B1-side
imputation occurs, the contrast is recomputed with those items excluded and
published alongside.

### 3.3 Binding co-criterion

`neither_A1 ≤ neither_B1 + 10pp`. If A1 wins the primary metric while breaching
that cap, the claim **fails**. Hedging is not trust.

### 3.4 Worst-case sensitivity, published alongside the primary result

The whole contrast is recomputed with **every `neither` in A1 counted as
`stale`** — punitive imputation on the treatment arm only, as a clinical trial
would do. This is published next to the primary number, not in an appendix. If
the effect does not survive it, the writeup says so in the headline.

This also removes most of the load from the exact value of the cap in §3.3.

### 3.5 Thresholds are a priori judgments, not derivations

There is no literature anchor for either number and inventing one would be worse
than admitting it.

- **15pp** minimum effect: roughly one wrong assertion in seven converted.
- **10pp** `neither` cap: extra caution is allowed, systematic refusal is not.

`cap < threshold` is deliberate: hedging within the cap can buy at most ~5pp on
the conditional metric (with B1 at 60% conditional, `(0.60 − 0.10)/0.90 = 55.6%`),
a third of the threshold, so it cannot manufacture a pass on its own.

### 3.6 Unit of analysis and power

**The unit is the item, not the trial.** Trials within an item are not
independent. Per-item conditional rates are computed per arm, paired by item, and
the CI on the mean paired difference is bootstrapped over items (10,000
resamples, BCa).

**Power is computed from a closed-form conservative bound, committed before
calibration.** Revision 2 said the calibration run would estimate "the
between-item SD of the paired difference" — but calibration is **B0 only**: it
contains no A1 runs, no B1 runs, and no pairs, so that SD is not observable in
those data. It was a promise its own inputs could not keep.

Instead: a binomial worst-case bound on per-item variance at `k` repetitions, an
inter-item heterogeneity term taken from the B0 rate spread of the surviving
items as a declared conservative proxy, and **correlation between arms assumed
zero** (the pairing can only help). The formula and the simulation script are
committed before calibration.

**Why the proxy is conservative**, argued rather than asserted: the B0 rate
spread at 4 repetitions is inflated by binomial noise (per-item rates can only
take the values 0, .25, .5, .75, 1) and narrowed by the ≥50% selection cut. At 4
reps the noise term dominates the range restriction, so the proxy overstates the
true between-item SD — erring toward demanding more data, not less.

**Selecting `n` and `k`.** "Power ≥ 0.80" is a constraint, not a choice: many
`(n, k)` pairs satisfy it. The committed script picks in a fixed order —
`k` first, from a floor that comes from §3.2 rather than from power: `k` must be
large enough that an all-`neither` cell is negligible (`0.5^k ≤ 1%`, so `k ≥ 7`),
because a small `k` inflates the empty-cell rate toward the 10% invalidation
ceiling. Then `n` is solved for power at that `k`. Timing is what keeps this
legitimate: the **rule** is committed before calibration, the **numbers** fall
out of it afterwards.

### 3.7 Falsification

The claim fails if the bootstrap 95% CI on the primary contrast includes zero, or
the point estimate is below 15pp, or the `neither` cap is breached, or the
undefined-cell rate exceeds 10%.

**A negative result is publishable and plausible.** FastEndpoints keeps a
hand-written bundle fresh with a process gate in `AGENTS.md` and no `stale_after`
at all: the write side may make the read side's metadata redundant.

## 4. The trap: why most versions of this experiment are worthless

If the superseded document reads as obviously old, any competent model avoids it
with or without frontmatter, and the experiment measures prose, not metadata.

**Design rule: the superseded document must be the more attractive answer.** It
is longer, more specific on the fact under test, and written in the question's
exact terminology; the replacement mentions the same fact more briefly, the way a
real supersession usually does. The only signal distinguishing them is the
frontmatter. Whether an item achieves this is decided operationally in §7.

## 5. Arms

Identical prose in every arm. Only frontmatter and the consumer instruction vary.

| Arm | Frontmatter | Instruction | Role |
|---|---|---|---|
| **B0** | stripped to `type` / `title` / `description` | none | descriptive |
| **B1** | stripped | operational, field-free | **primary control** |
| **A0** | full lifecycle + trust fields | none | descriptive |
| **A1** | full lifecycle + trust fields | field semantics (§5.3–§5.5) | **primary treatment** |

**Instructions are frozen verbatim and matched in force.**

> **B1:** "Some documents in this corpus may have been superseded by others. Do
> not assert superseded facts; always prefer the most current information."

> **A1:** "Some documents in this corpus may have been superseded by others. The
> YAML frontmatter tells you: `status: deprecated` marks a document kept for
> history that is no longer current (§5.4); content is stale when today is on or
> after its `stale_after` date (§5.5); a `verified` entry by a `human:` actor
> marks human-reviewed content, and no `verified` key means unverified (§5.3). Do
> not assert superseded facts; always prefer the most current information."

Same opening, same imperative, same closing sentence; A1 adds the field
semantics, worded from the spec text at the pinned commit rather than
paraphrased. **The label matters:** revision 2 called this "the §5.3 reading
rule", which was wrong twice — §5.3 covers only the `verified`-derived tier,
while the instruction spans §5.3, §5.4 and §5.5. A1 is *a consumer told the field
semantics*, not *a reference implementation of §5.3*.

## 6. Corpus

**Invented system, invented names, unguessable values.** If the subject were a
real project the model could answer from pretraining rather than from the corpus.
Every fact under test is a value no model can know.

Each item is a pair of documents stating different values for the same fact.

**Filenames are neutral and non-orderable** — revision 1 used
`<topic>-<successor>.md`, signalling the succession through a non-metadata
channel in *every* arm.

**Structure: 6 supersession shapes × 8 candidate items = 48 candidates** — a
limit that changed, a default that flipped, a renamed identifier, a reversed
recommendation, a removed capability, a changed precedence order. Revision 1 used
24 distinct shapes, i.e. n = 1 per shape: high authoring cost, no per-shape power.

## 7. Item validation, and the bias it would otherwise introduce

An item counts only if it traps: in **B0**, its **raw** stale rate must be
**≥ 50%** (raw, not conditional — in B0 with the base prompt and forced schema,
`neither` should be rare, and if it is not, that is itself reportable).

**This selection must not touch the data used for the comparison.** Selecting
items by B0 performance and then comparing arms on those same runs conditions on
the outcome variable and biases the result — invisibly, and in our favour.

1. **Calibration:** B0 only, 4 repetitions × 48 candidates = 192 runs.
2. **Discard calibration data entirely.** It selects items and feeds the
   heterogeneity proxy of §3.6. It never enters a result.
3. **Measurement:** all four arms, fresh runs of the surviving items.

**Pre-registered contingencies.** The 50% threshold is never lowered post hoc. If
fewer items survive than §3.6 requires: author more candidates and re-calibrate,
or run underpowered and say so in the headline, not a footnote. Surviving items'
measurement-run B0 rates are reported per item as the real evidence of trap-ness,
since selection on 4 reps regresses to the mean.

## 8. Harness

Concrete values, frozen in `harness.yaml` and included in the tagged commit of
§13. No placeholders: revision 2 wrote "declared, not implied", which declared
that something would be decided later.

- **Model:** `claude-opus-5`, version string recorded per trial; named in the
  writeup, not anonymised.
- **Execution surface: the `claude` CLI in headless mode** (`--backend cli`,
  revision 6), one process per trial, because the machine running this has no
  Anthropic API credentials and the protocol will not pretend otherwise. The
  Messages-API backend stays in `run.py` and is still the reference path. What
  changes, stated rather than buried: the file-read tool is the CLI's `Read`
  (absolute paths, so the trial directory is named in the prompt and its name is
  therefore neutral, §6), the per-trial identifier published under §13 is the
  CLI's `session_id` rather than a response `id`, and `usage` is the CLI's
  accounting including its own cached system prompt, which makes per-trial token
  counts a property of the harness and not of the item. Frozen and identical
  across arms as before: model, `effort`, one allowed tool, `--permission-mode
  dontAsk`, hooks disabled, and a fixed system prompt committed in `run.py`
  instead of the CLI's default, so a developer machine's configuration cannot
  enter a trial.
- **Sampling: not configurable, and that is the correct condition.** `claude-opus-5`
  rejects `temperature`, `top_p` and `top_k` with a 400; the Messages API exposes
  no seed parameter on any model. Revision 3 specified "temperature 1.0" and
  "seeds recorded per trial" — neither is implementable, and a pre-registration
  freezing two impossible values would have been discovered at the first API call,
  after the tag. What the removed knobs were there to guarantee still holds: the
  quantity measured is a *rate* over the model's answer distribution, and the
  deployment default is not near-deterministic, so repetitions are not redundant.
- **Frozen instead, because these do change behaviour and are settable:**
  `output_config.effort` and the `thinking` configuration, pinned in `harness.yaml`
  and identical across arms. Leaving `effort` implicit would let its default drift
  between the calibration and measurement runs without a diff to show for it.
- **Reproducibility is statistical, not bit-exact,** and the protocol says so
  rather than promising a determinism the API does not offer. Recorded per trial:
  the response `id`, the resolved model version string, `usage`, and the full
  request body.
- **Corpus delivery:** each trial exposes a directory containing the item's two
  documents plus **6 distractor documents** drawn from other items, read through
  a file-read tool. File order and directory position randomised per trial.
- **Distractor frontmatter matches the arm.** In the A arms distractors carry
  plausible full frontmatter; in the B arms they are stripped like everything
  else. Otherwise the target pair would be identifiable simply by being the only
  documents with frontmatter.
- **At least 2 of the 6 distractors are themselves `deprecated`**, on facts that
  are not under test. Without this the superseded document is the *only*
  `deprecated` file in the directory, and A1's task collapses from "judge
  freshness" into "find the deprecated one" — a free gift to the treatment that
  any sceptic would spot. Same reasoning for `stale_after`: distractor dates
  straddle the injected "today" in both directions.
- **Base prompt** identical across all four arms, instructing the agent to answer
  only from the corpus — without it, invented values produce refusals and
  `neither` explodes.
- **Injected current date:** a fixed "today", identical across arms, and placed
  **between** the two documents of every item: on or after the superseded
  document's `stale_after`, and strictly before the replacement's. Asserted per
  item at preflight.

That last point would otherwise have silently voided a third of the experiment.
The spec defines staleness as **`today >= stale_after`** (§5.5): a past
`stale_after` is inert if the model has no idea what day it is. Without an
injected date, one of the three fields under test is not tested at all, and
nothing in the results would reveal it.

Revision 4 wrote that rule as "later than every `stale_after` in the corpus",
which is worse than imprecise, it is unsatisfiable and self-defeating. It
contradicts the straddling requirement two bullets above, which needs distractor
dates on both sides of "today". And taken literally it makes the *replacement*
stale too, so the treatment arm is told every document is out of date and the
item has no correct answer left to give. A rule that voids the experiment it is
meant to protect, in the very section written to stop exactly that, is worth
recording rather than quietly correcting.

## 9. Grading

Deterministic, on a forced answer schema. The question prompt requires the answer
to end with `ANSWER: <value>`, and **only that field is graded**.

Revision 1 graded by string-matching the whole response, which breaks on the most
likely answer shape of all: *"it was F_old, now it's F_new"* contains both values,
and "asserts F_old" is a semantic judgment string matching does not implement.

`stale` if the field equals `F_old`, `fresh` if `F_new`, `neither` otherwise. No
LLM judge on the primary metric.

**Grader fidelity is tested adversarially**, not only on clean correct answers:
"was F_old, now F_new"; both values in prose with the correct one in the field;
F_old quoted in order to reject it; numeric formatting variants.

## 10. Integrity checks

- **Field identity across arms:** bodies **and** `type` / `title` /
  `description` byte-identical between arms for every document. Asserted before
  each run; the run aborts on any difference.
- **No leakage:** the questions file never contains `F_old` or `F_new`.
- **Independence:** one fresh agent per (item, arm, repetition), no shared context.

## 11. Scale

- **Calibration:** 192 runs (48 candidates × 4, B0 only). This is *larger* than
  revision 1's calibration, deliberately: more candidates lower the risk of
  triggering the §7 re-calibration contingency, which is the expensive failure.
  Revision 2 claimed budget had been "shifted away from calibration" while
  calibration had in fact grown — an internal contradiction in a document whose
  whole argument is honesty.
- **Measurement:** repetitions weighted toward the primary arms A1 and B1; A0 and
  B0 are descriptive and get fewer. Final numbers set by §3.6.

## 12. What a positive result would and would not support

**Scoping, in the headline rather than the footnotes.** B1 has **no recency
channel at all** by construction: §4 makes the prose favour the superseded
document and §6 neutralises the filenames. The control cannot obey its own
instruction even in principle. So A1 − B1 is a **mechanism demonstration** — the
consumer uses the channel when the channel exists — and **not** an estimate of
the marginal value of trust metadata in a real corpus, where prose, filenames,
dates in the text and repository history all carry recency signal. A0 − B0 is
reported prominently as the descriptive estimate of the passive effect.

It would support: a consumer reading a bundle with v0.2 lifecycle and trust
frontmatter asserts superseded facts less often than one reading the same prose
without it, given an equally forceful instruction.

It would **not** support: that OKF makes agents better, that bundles save tokens,
or that the metadata beats a write-side process gate.

Further declared confounds: a single named model, and a synthetic corpus — which
is where a metadata effect is *most* likely to appear, because there is no other
signal to go on. A robustness replication of the primary contrast on a second
model from a different family is run if budget allows.

## 13. Pre-registration and reproducibility

For a project whose reputation rests on measured honesty, a positive result
without this package is indefensible against "you adjusted it afterwards".

- Protocol, item set, `harness.yaml`, power formula and analysis script are
  **committed and tagged before the measurement run begins**.
- Published with the result, favourable or not: the full corpus, the questions,
  the grader, and every transcript with its per-trial response `id`, model
  version string and request body (§8 — there are no seeds to publish).

## 14. Open questions this protocol does not answer

- Does a supersession **link** outperform the trust fields? If so, the spec has a
  gap (§2).
- Does read-side metadata beat a **write-side process gate** of the FastEndpoints
  kind? Probably the more important question, and a different experiment.

## 15. Revision history

- **Rev 5 → 6.** No blocker, one honest substitution: the environment has no
  Anthropic API credentials, so trials run through the `claude` CLI in headless
  mode instead of the Messages API. This is an execution-surface change and it
  is recorded here rather than treated as configuration, because §13's
  reproducibility package promises specific per-trial artefacts and two of them
  now have a different shape (`session_id` for the response `id`; CLI-side
  `usage`, which counts the harness's own cached prompt). The rest of §8 is
  pinned harder than before, not looser: a fixed system prompt in place of the
  CLI's default, hooks disabled, one allowed tool, and a trial directory name
  that no longer spells out the item and the arm, since the CLI backend puts
  that path in the prompt where the API backend never did.

- **Rev 1 → 2.** Five blockers: ambiguous primary contrast; no analysis plan and
  an underpowered criterion; grader undefined on the most likely answer shape; no
  harness section, hiding the inert-`stale_after` failure; degenerate win via
  refusal. Plus matched instructions, supersession link removed, reproducibility
  package, neutral filenames, 6×8 shapes.
- **Rev 4 → 5.** One blocker, and it was hiding inside rev 4's own fix: §8's
  injected-date rule ("later than every `stale_after` in the corpus") both
  contradicted the distractor-straddling rule and marked the replacement document
  stale, leaving the treatment arm no fresh answer. Restated as a per-item
  sandwich, checked at preflight. Also: a trial with duplicate filenames now
  aborts, since it would silently deliver fewer documents than the design says.
- **Rev 3 → 4.** One blocker, found by checking §8 against the API instead of
  against memory: revision 3 froze two harness values that do not exist.
  `claude-opus-5` rejects `temperature` with a 400, and the Messages API has no
  seed parameter — so the section revision 3 added specifically to remove
  placeholders had itself specified an impossible configuration, and the
  reproducibility package in §13 promised seeds it could never publish. Replaced
  with the settable knobs that actually change behaviour (`effort`, `thinking`)
  and with per-trial response ids in place of seeds.
- **Rev 2 → 3.** Two blockers, both created by the rev-2 patches: the power
  analysis estimated a quantity absent from its own input data (§3.6), and the
  conditional metric was undefined precisely where the treatment arm concentrates
  refusals (§3.2). Plus: harness values instead of placeholders (§8), the "§5.3
  reading rule" mislabel (§5), the B1-has-no-recency-channel scoping moved into
  the headline (§12), thresholds declared arbitrary with rationale (§3.5),
  identity check extended beyond bodies (§10), calibration budget contradiction
  admitted (§11), spec pinned to a commit (header).
