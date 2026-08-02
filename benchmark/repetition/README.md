# Repetition: does a bundle pay across sessions?

The [first benchmark](../README.md) gave each agent one question in a fresh
session, so it priced a single question — and said so. But the cost a bundle is
actually adopted against accrues *across* sessions: every fresh agent re-derives
the same knowledge from source, or a human re-explains it, conversation after
conversation. This protocol measures that. It is the experiment
[#28](https://github.com/scaccogatto/okf-skills/issues/28) tracks, and the one
[results.md](../results.md#what-to-measure-next) promised.

## Design

**One repository, three states.** `okf-skills` at commit `2ed7902`, exported
three ways:

- **bundle** — the repo as it ships, `.okf/` included.
- **control** — the same tree with `.okf/` and `docs/self.html` deleted
  (`self.html` is the rendered bundle; the first benchmark learned this the
  hard way).
- **flat-notes** — the control tree plus `NOTES.md`: every `.okf` concept body,
  frontmatter stripped, links flattened to text, concatenated in path order by
  the script below. Same knowledge, no structure. **Without this arm a bundle
  win advertises writing-things-down, not OKF.**

**Eight tasks in a fixed order, each a fresh session.** One agent per task, no
shared context, same model across arms, read-only. The tasks
([tasks.md](tasks.md)) draw on five knowledge clusters, and every cluster but
one is needed by at least two tasks — that overlap is the point: it is what a
single-question design cannot see being re-derived.

**A scripted colleague, identical in all three arms.** Each agent gets an
`ask_colleague(question)` tool wired to a cheap model at temperature 0 whose
system prompt is the block below and whose only knowledge is
[faq.md](../faq.md) — the ground-truth facts written the way a teammate would say
them. Every call is counted by the runner as one **human turn**. Agents in all
arms are told the same thing: *"a colleague is available for questions; prefer
finding answers yourself."* In the bundle arm the agent should rarely need it;
in the control arm it is how the why-facts that live only in ADR prose get in.
That asymmetry is the phenomenon, not a leak.

> You are a senior engineer on this project answering a colleague's question.
> Answer ONLY from the FAQ you have been given. If the FAQ does not cover the
> question, reply exactly: "I don't know — check the repo." Keep answers under
> 120 words. Never mention the FAQ itself or any file it does not name.

## What is measured

- **cumulative tokens** — harness-billed, summed over the eight sessions of a
  sequence. The primary cost signal, and this time a cross-session one.
- **human turns** — `ask_colleague` calls, counted by the runner (not
  self-reported, an improvement over the first benchmark's file counts).
- **claims hit** — per task, against the claim lists in
  [tasks.md](tasks.md), graded blind exactly as
  [before](../README.md): opaque ids, no arm labels.
- **contradictions** — tasks.md names pairs of tasks whose answers state the
  same fact; a grader checks each pair for contradiction, blind to arm.

## Pilot, then the run

**Pilot at n=1** (3 arms × 8 tasks = 24 sessions) exists to calibrate the
scripted colleague, which is the fragile part: answer too well and the control
arm wins for free; answer too poorly and it is a strawman. Calibration check:
audit the pilot transcripts — every FAQ-covered question must have received the
matching facts, every uncovered one the refusal line. Adjust faq.md wording
only for delivery, never to add or remove facts, and re-pilot if it changes.

**Full run at n=3** (72 sessions, fresh sequences throughout). At the first
benchmark's per-session costs, expect the full run around 3M tokens — decide
that budget before starting, not at task five.

## What would falsify what

- Control ≈ bundle on cumulative tokens *and* human turns → the repetition
  pitch fails on a repo of this kind, and we publish that.
- Flat-notes ≈ bundle on all four metrics → writing-things-down is the value
  and OKF's structure added nothing here; also published.
- Bundle beats control but not flat-notes on consistency → structure buys
  stability, not economy. All three outcomes are worth the run.

## Limits, stated up front

- **A floor, not a typical value.** This repo's code carries its own reasoning
  (the first benchmark documented this), so its control arm re-derives more
  cheaply than a typical repo's would. Whatever difference appears here is a
  lower bound.
- **Read-only arms.** The bundle arrives pristine and nobody maintains it
  mid-sequence, so the *write* side of a bundle's cost — authoring and upkeep —
  is not priced. A full cost-of-ownership number needs that side too.
- **The task authors wrote the FAQ.** Same shape as the first benchmark's
  "the grader wrote the questions" limit; the mitigation is the same — every
  task is verified answerable from source in every arm, the FAQ is committed
  before the run, and the transcripts are published.
- **The colleague is a model.** A real teammate misremembers, asks back,
  volunteers context. Temperature 0 against a fixed FAQ is a cleaner instrument
  and a less realistic one.

## Reproducing

```bash
git archive 2ed7902 | tar -x --one-top-level=bundle
cp -r bundle control && rm -rf control/.okf control/docs/self.html
cp -r control flat-notes
python3 - <<'EOF'
import re, pathlib
out = []
for p in sorted(pathlib.Path('bundle/.okf').rglob('*.md')):
    if p.name in ('index.md', 'log.md'):
        continue
    body = re.sub(r'\A---.*?^---\s*', '', p.read_text(), flags=re.S | re.M)
    body = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', body)
    out.append(body.strip())
pathlib.Path('flat-notes/NOTES.md').write_text('\n\n---\n\n'.join(out) + '\n')
EOF
```

Then run the eight tasks of [tasks.md](tasks.md) in order against each arm —
fresh agent per task, `ask_colleague` wired to [faq.md](../faq.md) with the prompt
above — and grade blind against the claim lists. Publish the transcripts,
per-session token counts, turn counts, and the grading key, as
[`../answers/`](../answers/) did.
