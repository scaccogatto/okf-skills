---
type: Decision
title: Benchmark trustability, not the adoption pitch
description: Bring back a benchmark after #32 removed one, measuring the one claim the spec actually makes and nobody has tested.
tags: [adr, benchmark, trust, evidence]
status: stable
generated: { by: agent:claude-opus-5, at: "2026-09-02T00:00:00Z" }
verified: { by: agent:claude-opus-5, at: "2026-09-02T00:00:00Z" }
---

# Context

[#32](https://github.com/scaccogatto/okf-skills/pull/32) removed `benchmark/`
entirely, and the reason was not that it was badly run. It measured better
answers, cheaper reading, and cross-session repetition cost — and across the
canonical spec, `token`, `cost`, `efficiency`, `save` and `repetition` each occur
**zero** times. It measured the ecosystem's adoption pitch, not the standard this
toolkit implements.

Two things changed since.

`aws-samples/sample-okf-llm-wiki` published a serious OKF benchmark: BIRD
mini_dev, EX 74.0, 500 independent agents, graded by bird-bench's unmodified
evaluator, with gold isolation, a grader-fidelity check, and its own confound
stated in a section called "Reading the comparison honestly". It measures
**sufficiency** — that a bundle carries enough structure for an agent to work
from — which is a real §1 claim, and it measures it well.

That leaves **trustability**, the spec's own headline ("above all trustable"),
untested by anyone.

# Decision

Build a benchmark for trustability, and only that. The falsifiable form: given a
corpus containing both a superseded document and its replacement, does the v0.2
lifecycle and trust frontmatter — `status` (§5.4), `stale_after` (§5.5), and the
tier derived from `verified` (§5.3) — reduce how often a consumer asserts the
superseded fact?

Protocol in [`benchmark/trust/PROTOCOL.md`](https://github.com/scaccogatto/okf-skills/blob/main/benchmark/trust/PROTOCOL.md),
tracked in [#40](https://github.com/scaccogatto/okf-skills/issues/40). It has now
been run: pre-registration frozen at `trust-benchmark-prereg-rev8`, 946
measurement trials, result in
[`benchmark/trust/RESULTS.md`](https://github.com/scaccogatto/okf-skills/blob/main/benchmark/trust/RESULTS.md).

The call to measure trust rather than re-run sufficiency was made by
`human:scaccogatto`; the protocol was drafted by an agent and rejected twice in
adversarial review before being cleared as executable.

# Outcome

**The primary result is invalid under the protocol's own §3.2 rule** — 16.3% of
items have no committed answer in a primary arm against a 10% ceiling — and the
effect it would otherwise have reported is at the ceiling: a 97.7pp reduction in
conditional stale rate, 93.7pp under the punitive worst case. Both facts have
one cause: the control does not answer. 116 of its 123 `neither` are the literal
token `unknown`.

Two descriptive readings carry more than the headline. **The instruction alone
does nothing** (B1 − B0 = 0.0pp): telling a consumer to prefer current
information, with no metadata to act on, changed nothing. **The metadata alone
does everything** (A0 − B0 = −97.7pp): the fields are read without being
explained. On this corpus the frontmatter carries the whole effect and the
wording carries none of it.

The scoping is not a footnote. The control has no recency channel by
construction — the corpus was rebuilt twice to remove the ones the first draft
leaked — and items were selected for trapping the control, so "100% → 0%" means
*on items where the control was already known to fail*, not *the control fails
everywhere*. This is a mechanism demonstration, not an estimate of what trust
metadata is worth in a real corpus.

# Consequences

* `benchmark/` returns to the repo, and its first paragraph has to justify why
  this is not the thing #32 deleted. If that justification ever stops holding,
  this benchmark goes the same way.
* The result may be negative, and a negative result gets published. FastEndpoints
  keeps a hand-written bundle fresh with a process gate in `AGENTS.md` and no
  `stale_after` at all: the write side may make the read side's metadata
  redundant.
* The design deliberately strips the control arm of every recency signal, so a
  positive result demonstrates a **mechanism** — the consumer uses the channel
  when it exists — and does not estimate what trust metadata is worth in a real
  corpus. The writeup must lead with that, not bury it.
* A pre-registration can only freeze parameters that exist. Revision 3 froze
  `temperature: 1.0` and "seeds recorded per trial" as the concrete values that
  were supposed to remove the section's placeholders — but `claude-opus-5`
  rejects `temperature` with a 400, and the Messages API has no seed parameter at
  all. Checking §8 against the API instead of against memory is now part of
  clearing a revision, because the tag would have frozen an impossible
  configuration and the reproducibility package would have promised seeds it
  could never publish.
* Two questions are left open and named rather than quietly avoided: whether a
  supersession *link* would beat the trust fields (v0.2 defines no such field, so
  that would be a gap in the spec), and whether read-side metadata beats a
  write-side process gate at all.
