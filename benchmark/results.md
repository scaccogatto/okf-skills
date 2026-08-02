# Results

Run on 2026-07-27 against `okf-skills` at `e91720e`. Method and limits:
[README](README.md). Questions and claim lists: [questions.md](questions.md).

## Correctness

Claims hit, out of the ground-truth list for each question. Graded blind.

| Question | with `.okf/` | without | winner |
|---|--:|--:|---|
| Q1 lookup | 4/4 | 2/4 | bundle |
| Q2 lookup | 4/5 | 3/5 | bundle |
| Q3 cross-cutting | 3/4 | 3/4 | tie |
| Q4 change-site | 3/4 | 4/4 | **no bundle** |
| Q5 cross-cutting | 5/5 | 5/5 | tie |
| Q6 cross-cutting | 3/4 | 3/4 | tie |
| **total** | **22/26 (85%)** | **20/26 (77%)** | |

Two wins, one loss, three ties. No answer in either arm contained a false
statement — the failures are all omissions.

Eight points on twenty-six, at n=1 per cell, is not a result anyone should
quote as a headline. What is worth reading is **which** questions moved, because
that pattern is consistent and it is not the pattern the marketing would predict.

**The bundle won on "why".** Q1 asked why the plugin ships no hooks. Without the
bundle, the agent found the README's *"ships no hooks by design"* and the absence
of a hooks directory — it got the decision and the opt-in mechanism, and missed
the reasons entirely: that always-on hooks observing arbitrary sessions are
intrusive, and that they fail third-party marketplace safety review. Those two
claims exist in exactly one place in the repo, the ADR. Everywhere else, the
decision is stated without its rationale. Same shape on Q2, where the bundle arm
also recovered the *quadratic* growth claim that the code comment does not spell
out.

**The bundle lost on "where do I change this".** Q4 asked which file to edit and
what decides error-versus-warning. The bundle arm read the concept describing the
validator, answered from it, and missed that `--strict` / `--max-warnings` is what
turns warnings into a failure. The control arm read the source, and got
everything. The concept was a summary, and the question wanted the detail the
summary dropped — the bundle became a detour around the file that had the answer.

**Everything mechanical tied.** Q3, Q5 and Q6 are questions whose answers are
constants, control flow, and a code comment. Both arms found them and both arms
missed the same fourth claim. The bundle added nothing because there was nothing
to add.

So the shape of the finding: **a bundle earns its keep for the knowledge that has
no other home — decisions, rationale, the reason behind a number. For anything the
code itself states, it is neutral at best and a detour at worst.**

## Cost, within a session

Each agent answers one question in a fresh session and stops, so `tokens` here
prices a single question — what a bundle saves or wastes *across* sessions is
invisible to this design ([What to measure next](#what-to-measure-next)).
`tokens` is what the harness billed each agent — the honest effort number, and
the reason the self-reported file counts below are a footnote rather than the
headline. `files` is self-reported by each agent.

| Question | tokens, with `.okf/` | tokens, without | delta | files with/without |
|---|--:|--:|--:|--:|
| Q1 lookup | 38,672 | 38,655 | +0.0% | 2 / 3 |
| Q2 lookup | 33,869 | 33,899 | −0.1% | 2 / 1 |
| Q3 cross-cutting | 39,494 | 41,051 | −3.8% | 10 / 7 |
| Q4 change-site | 45,098 | 43,427 | +3.8% | 2 / 1 |
| Q5 cross-cutting | 50,090 | 48,434 | +3.4% | 2 / 2 |
| Q6 cross-cutting | 50,379 | 39,339 | +28.1% | 2 / 2 |
| **total** | **257,602** | **244,805** | **+5.2%** | 20 / 16 |

**The bundle arm cost more, not less.** 5.2% more tokens over six questions, and
it opened more files, not fewer. At n=1 per cell that total is inside the noise —
Q6 alone swings 28% with both arms reading the same two files — so the honest
reading is not "the bundle costs 5% more" but **"no measurable cost saving, in
either direction."**

That is worth saying plainly, because one claim made for a knowledge bundle is
that an agent reads three small files instead of three thousand lines. On this
repo, at this size, within a session, that saving did not appear.

## Why the saving did not appear here

Two properties of this repository, and one of this experiment's design:

**The code carries its own reasoning.** The threshold in Q2 is a named constant
with a four-line comment giving the measurement that set it. The severity rule in
Q4 is two methods on a dataclass. An agent that greps the source finds the *whole*
answer, rationale included, in one file. A repo whose comments say what and not
why would not behave this way — and most repos are that kind of repo.

**The repo is small.** Twelve concepts, a handful of scripts. Progressive
disclosure buys nothing when reading everything is already cheap. The bundle's
argument is about corpora that outgrow a context window, and this one does not.

**The design stops after one question.** The token cost usually cited for
adopting a bundle is repetition: every fresh session re-derives the same
knowledge from source, or a human re-explains it, conversation after
conversation. That
cost accrues across sessions, and an experiment that ends after one question
ends before the meter starts. Q1's control arm is the mechanism in miniature: it
missed the no-hooks rationale, and in real use that miss does not stay an
omission — it becomes a person supplying the rationale by hand, this session and
again the next. Here it was graded, and the session ended.

None of the three says OKF does not work. All three say *this benchmark cannot
see the cost effect a bundle is bought for*, which is a different and more
useful thing to know than a favourable number would have been.

## What this changes about how the bundle is pitched

The README's claim used to lean on progressive disclosure — read three small files
instead of three thousand lines. This experiment does not support that on a repo
this size, and says so.

What it does support is narrower and more defensible: **write down what the code
cannot say.** A concept that restates a constant is a maintenance liability that
bought nothing here. A concept that records why the constant is 1,000
answered a question the codebase otherwise could not.

That is a bar for what belongs in a bundle, and it came out of a result that went
the wrong way.

## What to measure next

Three experiments would test what this one could not. Each is outlined below —
enough to argue with, not yet a full protocol — and
[#21](https://github.com/scaccogatto/okf-skills/issues/21) is the open thread.

**Scale.** The same design on the corpus this repo cannot be: large enough that
reading everything is not an option, with comments that say what rather than
why. That is where progressive disclosure should show up as a within-session
saving — and where six questions at n=1 would no longer be enough.

**Repetition.** The cost this design truncates. Two arms as before, but a
*sequence* of tasks per arm with overlapping knowledge needs, run as fresh
sessions — the way agents are actually used. In the bundle arm the knowledge
persists in `.okf/` and every session reads it; in the control arm it is
re-derived from source, or supplied by a scripted "user" who answers what the
agent cannot find, the way a colleague does today. Measure cumulative tokens,
human turns, and whether the answers stay consistent from session to session.
That is where "the bundle keeps you from explaining the same concepts over and
over" stops being an assertion — today it is exactly as unmeasured as
progressive disclosure was before this file existed. One arm this experiment
must carry: the same knowledge as a flat notes file, no frontmatter, no links.
Without it, a win here advertises writing-things-down, not OKF.

**Trust.** The experiment the spec would nominate. This one ran against a
bundle the limits call unusually good — current, curated, verified — which is
exactly where v0.2's machinery is idle: provenance, trust tiers and staleness
earn their keep only when knowledge might be wrong. So seed the bundle with
realistic rot — concepts past their `stale_after`, `status: deprecated`,
unverified machine-written entries, one concept subtly wrong against source —
and measure whether agents *calibrate*: discount the unverified, re-check the
stale, refuse the deprecated. The metric flips from omissions to false
statements: does the wrong concept's error reach the answers, and do the
signals stop it? Q4's loss is this failure in miniature — an agent
over-trusting a summary — and §5 exists so a consumer does not have to.
