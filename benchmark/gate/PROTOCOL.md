# Write-side gate versus read-side metadata — protocol

**Status:** revision 1, pre-registered before the measurement run. Tracked in
[#48](https://github.com/scaccogatto/okf-skills/issues/48); the question is the
one [#40](https://github.com/scaccogatto/okf-skills/issues/40) named in its §14
and called "probably the more important question".

**Spec under test:** OKF **v0.2**, as vendored at `skills/okf/reference/SPEC.md`,
okf-skills commit `c68f9f2`.

## 1. Why this exists

#40 established that the v0.2 trust fields work as a channel: given a corpus
where frontmatter is the only recency signal, a consumer reads `status`,
`stale_after` and `verified` and stops asserting superseded facts, without being
told what those fields mean. It also established, by accident and at some cost,
that making the metadata matter required removing every other signal: the first
corpus trapped 0 of 48 items because ordinary documentation prose already
communicates recency.

FastEndpoints ships a hand-written `.okf/` bundle in a repository that pushes
daily. The bundle does not drift. It carries no `stale_after` at all, and its
freshness rule lives in prose in `AGENTS.md`: *a task is not finished until the
bundle is synced or explicitly declared unaffected*. If a write-side gate keeps a
bundle fresh, then read-side metadata is redundant in practice even though it
works in a laboratory. That is the question here.

## 2. The claim

**Claim.** A write-side process gate reduces the rate at which a consumer asserts
superseded facts at least as much as read-side trust metadata does.

**Falsifiable form.** For a system whose documented fact changes, run the
pipeline that actually produces staleness — an agent applies the change, then a
*different* agent answers a question from the resulting repository — and compare
end-to-end error rates.

**The asymmetry that shapes the design.** `status: deprecated` and `verified`
both require someone to act at write time, which is exactly what the gate also
requires: comparing them would compare two disciplines rather than two
mechanisms. **`stale_after` is the only field that degrades without anyone
acting** — a date set in advance expires on its own. So the read side is
measured in the state a repository reaches when the writer does nothing, and the
`stale_expired` state is the one that carries the claim.

## 3. Arms and stages

### Stage W — the writer, and Stage E — the pipeline it feeds

An agent is given a repository (`config/settings.yaml` stating the old value,
`docs/<file>.md` documenting it) and asked to apply the change to the
configuration. Two arms:

| Arm | What the agent is told |
|---|---|
| **nogate** | apply the change |
| **gate** | apply the change, and *"Read `AGENTS.md` first and follow the repository's conventions"* |

`AGENTS.md`, frozen verbatim in `pipeline.py`:

> A task is not finished until the documentation in `docs/` is synced with the
> change, or the task explicitly declares the documentation unaffected.

**The ungated arm is not a formality.** An agent may sync documentation
spontaneously, and that spontaneous rate is the baseline against which the gate's
value is measured. It is plausibly the most interesting number in the experiment.

**Stage E closes the pipeline**: a fresh consumer answers the item's question
against the repository the writer left behind. This is deliberate rather than
economical — the deterministic file signals cannot separate "synced" from
"mentions the new value somewhere", because `f_old` legitimately survives in a
correctly updated document (the writer probe found one where the old value is a
row in a table of alternatives). Rather than build a semantic grader for
documents, the pipeline is closed and the consumer's answer is the outcome.

The document the writer meets carries **no staleness signal of its own**: status
`stable`, no `verified`, and `stale_after: 2028-12-31`. At the moment of the
change nothing says the document is out of date; whether it ends up saying so is
the outcome under test. (The first writer probe missed this and graded every run
as "already deprecated", because the corpus authors that document as the
superseded one.)

### Stage C — the read side, without a writer in the loop

Per item, four corpus states are built deterministically and answered by the same
consumer harness:

| State | Document | Frontmatter |
|---|---|---|
| `synced` | the replacement | current, `verified` |
| `stale_unmarked` | the superseded one | stripped to `type`/`title`/`description` |
| `stale_expired` | the superseded one | `status: stable`, expired `stale_after`, no `verified` |
| `stale_marked` | the superseded one | `status: deprecated`, expired `stale_after`, no `verified` |

The three stale states share a byte-identical body and differ only in lifecycle
frontmatter, asserted in the test suite. `stale_expired` − `stale_unmarked` is
the read-side effect that survives a writer who does nothing; `stale_marked` −
`stale_unmarked` is the effect when someone did act, which is the state
comparable to a gate.

`synced` is a sanity control: if a consumer gets that wrong, nothing else here
means anything.

## 4. The implementation artifact, and the correction it encodes

**Every consumer corpus, in every arm and every state, contains
`settings.yaml` stating the current value.** Without it a stale-document state
has no reachable correct answer, refusal becomes the correct behaviour, and the
metric is undefined by construction — which is precisely the failure that
invalidated #40's primary result. This is also the realistic setting: a repo's
code is present alongside its docs.

The artifact quotes the item's question verbatim as the setting's comment. That
is a deliberate simplification: it makes the artifact unambiguously about the
fact under test, identically in every arm, rather than leaving the consumer to
guess which key answers the question.

## 5. Metric and analysis, fixed before the run

**Primary metric: the raw stale rate** — the share of trials whose answer is the
superseded value — not #40's conditional rate. The departure is justified rather
than convenient: every state here has a reachable correct answer (§4), no arm is
instructed toward caution, and in `stale_expired` a refusal is defensible
behaviour rather than hedging. #40's conditional metric existed to stop an arm
winning by refusing; here refusal is reported separately and capped.

**Unit of analysis: the item.** Per-item stale rates, paired across arms or
states, mean paired difference, 95% CI bootstrapped over items (10,000
resamples).

**Effects are reported as reductions**: control minus treatment, so a mechanism
that helps produces a positive number. #40's committed analysis compared a signed
contrast against a positive floor and would have reported a perfect result as a
failure; no test exercised the direction. Here the direction tests are written
**before** the run (`tests/test_gate.py`).

**Contrasts, all pre-registered:**

1. **Write side:** `gate` − `nogate` on the Stage E stale rate.
2. **Read side, no writer:** `stale_expired` − `stale_unmarked`.
3. **Read side, someone acted:** `stale_marked` − `stale_unmarked`.

**Thresholds** (a priori judgments, as in #40 §3.5, with no literature anchor and
no pretence of one): an effect counts if its CI excludes zero **and** the point
estimate is at least **15pp**. Refusal (`neither`) rates are reported per arm and
per state; a mechanism whose refusal rate exceeds its comparator's by more than
**10pp** has bought its reduction with hedging and the reduction is reported as
such.

**Falsification.** The claim of §2 fails if the write-side reduction is below the
read-side reduction it is compared against — specifically, if `gate` − `nogate`
is smaller than `stale_expired` − `stale_unmarked` and the difference is outside
the CI. It is equally possible that **both** are small, which is a result about
the setting rather than about either mechanism, and it will be published as one.

## 6. What the probes decided, and why they are not evidence

#40's expensive lesson is that a run answers design questions a protocol cannot.
Two probes ran before this protocol was frozen; their data is published under
`runs/probe-*.jsonl` and **does not enter any result**.

- **Writer probe** (12 runs): every writer updated the configuration; 5 of 6
  *ungated* writers also edited the documentation unprompted. The gate's
  headroom is therefore small, and the measurement is sized to detect a small
  effect rather than to confirm a large one.
- **Consumer state probe** (32 runs): with the implementation artifact present,
  the stale rate is 3/8 in `stale_unmarked`, 1/8 in `stale_expired`, 0/8 in
  `stale_marked`, and 0/8 in `synced`. The read side has headroom, and the
  baseline error is far below #40's 100% precisely because the artifact is
  there.

Both probes also found defects in this harness (the writer's document carrying a
`deprecated` status it should not have; substring grading crediting untouched
documents), which is what they were for.

## 7. Scale

- Stage E: 20 items × 2 arms × 5 repetitions = 200 pipelines, 400 model calls.
- Stage C: 20 items × 3 stale states × 5 repetitions = 300 calls, plus the
  `synced` control at 1 repetition.
- Items are a fixed-seed sample of #40's 43 surviving items — a prefix would be
  alphabetical by shape and would silently make the item set one or two shapes.
  Shape composition of the sample is reported with the result.

Projected cost ~$200. Underpowering is possible and will be stated in the
headline rather than a footnote, as in #40 §7.

## 8. What no result here can mean

**A per-trial harness measures whether an agent obeys an explicit gate once. It
cannot measure the long-horizon discipline drift that actually separates a
write-side gate from pre-set metadata in a real repository.** A gate that holds
on trial one and erodes over six months of deadlines is indistinguishable here
from one that holds forever. If gated compliance sits at its ceiling — and the
probe suggests it does — then that sentence is most of the finding, and it is
still the honest answer to #40's §14.

Further declared limits: one model, one family; a synthetic repository with one
configuration file and one document, where a real one has hundreds and the
writer's attention is divided; and an agent writer rather than a human, which is
the case OKF is aimed at but not the only case that matters.

## 9. Reuse and pre-registration

Reused verbatim from #40 rather than rewritten: the frozen CLI invocation (safe
mode **and** the advisor disabled, both of which #40 paid to discover), the
injected date, the forced bare-value answer field with its `unknown` token, the
grader with its adversarial tests, and the 43 items its calibration validated as
traps.

Protocol, harness, analysis and tests are committed and tagged before the
measurement run. Corpus states, transcripts and every trial record are published
with the result, favourable or not.
