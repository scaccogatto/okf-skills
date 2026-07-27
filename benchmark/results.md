# Results

Run on 2026-07-27 against `okf-skills` at `e91720e`. Method and limits:
[README](README.md). Questions and claim lists: [questions.md](questions.md).

## Cost

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

That is worth saying plainly, because the usual claim made for a knowledge bundle
is that an agent reads three small files instead of three thousand lines. On this
repo, at this size, that saving did not appear.

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

## Why the saving did not appear here

Two properties of this repository, both of which weaken the bundle's case:

**The code carries its own reasoning.** The threshold in Q2 is a named constant
with a four-line comment giving the measurement that set it. The severity rule in
Q4 is two methods on a dataclass. An agent that greps the source finds the *whole*
answer, rationale included, in one file. A repo whose comments say what and not
why would not behave this way — and most repos are that kind of repo.

**The repo is small.** Twelve concepts, a handful of scripts. Progressive
disclosure buys nothing when reading everything is already cheap. The bundle's
argument is about corpora that outgrow a context window, and this one does not.

Neither is an argument that OKF does not work. Both are an argument that *this
benchmark cannot see the cost effect it was built to measure*, which is a
different and more useful thing to know than a favourable number would have been.

## What this changes about how the bundle is pitched

The README's claim used to lean on progressive disclosure — read three small files
instead of three thousand lines. This experiment does not support that on a repo
this size, and says so.

What it does support is narrower and more defensible: **write down what the code
cannot say.** A concept that restates a constant is a maintenance liability that
measurably bought nothing here. A concept that records why the constant is 1,000
answered a question the codebase otherwise could not.

That is a bar for what belongs in a bundle, and it came out of a result that went
the wrong way.

## If someone repeats this

The experiment worth running next is the one this repo cannot host: a corpus large
enough that reading everything is not an option, and a codebase whose comments say
what rather than why. That is where progressive disclosure should show up as a
cost saving, and where six questions and n=1 would no longer be enough.
