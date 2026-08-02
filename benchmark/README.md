# Does an OKF bundle actually help an agent?

Nobody in the OKF ecosystem publishes a number. This is ours, including the
cases where the bundle does not help — those are the interesting ones.

One scoping note. The claim under test — better answers, cheaper reading — is
the ecosystem's adoption pitch, not the spec's. The spec (§1) promises portable,
diffable, *trustable* knowledge, and stakes v0.2 on trust of agent-written
corpora — which this experiment never exercises, because its bundle is pristine
(see Limits). What is measured here is the question a user asks before
installing; the spec's own question is
[outlined as the next experiment](results.md#what-to-measure-next).

## Method

**One repository, two states.** `okf-skills` at commit `e91720e`, exported twice:
`with-okf/` is the repo as it ships, `without-okf/` is the same tree with `.okf/`
deleted. Nothing else differs. Every fact the questions ask about is present in
both arms — in code comments, the README, the CHANGELOG, or ADR prose. The bundle
is a **shortcut**, never the only source; the experiment asks whether the
shortcut pays.

**Fresh agent per question per arm.** 12 agents, no shared context, same model
(Claude Sonnet), read-only. Each is told only that it is answering a question
about an unfamiliar codebase at a given path. None is told the experiment is
about OKF, that a bundle exists, or that `.okf/` is worth reading.

**Six questions** ([questions.md](questions.md)) across three shapes: lookup,
cross-cutting, and change-site. Each carries a list of claims a correct answer
must contain.

**Blind grading.** Answers are stripped of their `FILES_OPENED` list, written to
files keyed by an opaque id, and handed to a separate grading agent that sees the
claim lists and nothing else — no arm labels, no key. It grades claim by claim.

The blinding is real but not perfect: an answer that cites `.okf/decisions/...`
announces its own arm, and the grader can read that. It holds better than it
sounds because the rubric is claim presence, which is close to mechanical — but
it is not a blind that would survive a subjective quality score, and it should
not be described as one.

## What is measured

- **claims hit** — of the ground-truth claims, how many the answer contains.
- **tokens** — what the harness billed each agent for its one-question session.
  The primary cost signal, and a within-session one by construction.
- **files opened** — self-reported by each agent.
- **tool calls** — self-reported by each agent.

Files and tool calls are self-reported, which is a real weakness: an agent can
undercount. They are reported as a coarse signal of effort, not a precise cost.

## The control arm had to be rebuilt

The first control arm was `with-okf/` minus `.okf/`. That is not a control:
`docs/self.html` is the **rendered bundle**, with all twelve concept bodies
embedded in its inline JSON, and it is committed to the repo. One control agent
found it and answered from it — correctly, and with the bundle's own prose.

The arm was rebuilt without `docs/self.html` and all six control agents re-run.
The first run is reported below as a finding rather than deleted: a repo that
publishes its bundle as a static page has two copies of its knowledge, and an
experiment that deletes only one of them measures nothing.

## Limits, stated up front

- **n = 1 per cell.** One agent per question per arm. Enough to see a large
  effect, not enough to resolve a small one. Treat single-question differences as
  anecdote and only the aggregate as signal.
- **One question per session.** Each agent answers a single question and stops.
  Whatever a bundle saves — or wastes — across sessions, by sparing the same
  knowledge from being re-derived or re-explained every time, is invisible here
  in either direction. The token numbers are within-session cost only; the
  cross-session experiment is
  [outlined in results.md](results.md#what-to-measure-next).
- **The repo documents itself in OKF**, so its bundle is unusually good. A bundle
  that has rotted would not behave like this one.
- **Self-reported effort**, as above.
- **The grader wrote the questions.** Blinding covers which arm an answer came
  from, not the choice of what to ask. A question set drawn from the bundle's own
  table of contents would flatter the bundle; these were drawn from the repo's
  behaviour and each verified answerable from source in both arms.

## Reproducing

```bash
git archive e91720e | tar -x --one-top-level=with-okf
cp -r with-okf without-okf && rm -rf without-okf/.okf
```

Then put each question from [questions.md](questions.md) to a fresh agent pointed
at one arm, with no other context, and grade the answers against the claim lists
with the arm labels hidden.

Results: [results.md](results.md). The graded answers are committed verbatim in
[`answers/`](answers/), with `key.txt` mapping each opaque id back to its arm —
so anyone can regrade them against a different rubric, or check that the claim
lists were not written to fit the answers.
