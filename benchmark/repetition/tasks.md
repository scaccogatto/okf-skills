# Task sequence

Eight tasks about this repository, run in this order, each in a fresh session.
They span the same three shapes as the [first benchmark](../questions.md) —
lookup, cross-cutting, change-site — but are built around five **knowledge
clusters** so that the same knowledge is needed again and again across
sessions. That repetition is what the experiment prices.

Every task is answerable in every arm: from `.okf/` in the bundle arm, from
`NOTES.md` in the flat-notes arm, and from code, README, and the scripted
colleague in the control arm. Grading is per claim and blind, as before.

## Clusters and where they recur

| Cluster | Knowledge | Needed by |
|---|---|---|
| A | upkeep enforcement: dormant Stop hook, `upkeep: enforced`, `OKF_HOOK=off`, no-hooks → dormant-hooks history | T1, T4, T7 |
| B | trust: §5.3 tier derivation, staleness §5.5, computed at render, stored nowhere | T2, T6, T8 |
| C | validator: §11 errors vs warnings, `--strict`, v0.1 legacy constructs, `--migrate` | T3, T4, T8 |
| D | distribution: plugin + skills.sh dual layout, `${CLAUDE_SKILL_DIR}`, portability constraints | T5, T4 |
| E | visualizer scale: `AUTO_COSE_MAX`, concentric fallback, the Chrome measurement | T6 |

Cluster E is the one singleton — kept because T6 needs a change-site anchor,
and flagged here so nobody reads its per-cluster numbers as repetition signal.

## Consistency pairs

The same fact stated in two sessions should not contradict itself. A blind
grader checks these pairs, contradiction yes/no:

- **T1 / T7** — the hook's activation and opt-out semantics.
- **T2 / T8** — how a trust tier is produced.
- **T3 / T8** — what `--strict` does to warnings.

---

## T1 — lookup (cluster A)

> Does anything in this toolkit *enforce* keeping the knowledge bundle updated
> after code changes, or is upkeep purely voluntary? Tell me the whole story,
> including how an end user can refuse.

**Claims required**

1. Yes — the plugin ships a `Stop` hook (`hooks/okf-stop-check.sh`), but it is
   dormant by default.
2. It activates only when a bundle opts in with `upkeep: enforced` in
   `.okf/index.md`'s frontmatter.
3. The user can force-disable it regardless of bundle settings with
   `OKF_HOOK=off`.
4. This superseded an earlier deliberate zero-hooks decision (always-on hooks
   are intrusive and risk failing marketplace safety review).
5. Soft mode still exists: the `templates/CLAUDE-okf.md` snippet pasted into a
   project's `CLAUDE.md`.

## T2 — lookup (cluster B)

> A concept renders with a "machine-confirmed" badge in the graph. What exactly
> produced that label, and what would I add to the concept to make it
> "human-reviewed"?

**Claims required**

1. The tier is derived at render time — it is stored nowhere.
2. Derivation (§5.3): no `verified` entries ⇒ unverified; `verified` by
   non-`human:` actors only ⇒ machine-confirmed; any `human:` actor ⇒
   human-reviewed.
3. So: add a `verified` entry whose actor is `human:<someone>`.
4. Why it is not stored: a stored tier is a stored opinion, and it goes stale —
   OKF records signals and lets consumers infer.

## T3 — change-site (cluster C)

> Our team's bundle was written a while ago and now fails CI, which runs this
> repo's validator with `--strict`. What are the most likely culprits, what is
> the one-command fix, and was the bundle ever actually non-conformant?

**Claims required**

1. Likely culprits: the v0.1 legacy constructs — `timestamp` and the body
   `# Citations` list — reported as warnings, which `--strict` turns into
   failures.
2. Their v0.2 replacements are `generated.at` and `sources`.
3. The fix is `--migrate`, which rewrites the bundle in place.
4. The bundle was conformant all along — §11's hard rules never mention those
   constructs.

## T4 — cross-cutting (clusters A, C, D)

> We want bundle upkeep enforced both while agents work *and* in CI, in a repo
> whose CI has no Claude Code. What does this toolkit give us for each side,
> and what must we turn on where?

**Claims required**

1. Session side: the dormant Stop hook, activated per bundle via
   `upkeep: enforced` in `.okf/index.md` frontmatter.
2. CI side: the composite GitHub Action (`action.yml`), which runs the
   validator — no Claude Code, no account, deterministic.
3. The action takes `bundle`, `strict` / `max-warnings` inputs and emits the
   JSON report as an output.
4. The two layers are independent and both opt-in; neither activates by merely
   installing the plugin.

## T5 — change-site (cluster D)

> I'm adding a new skill, `okf-diff`, with its own Python script. Lay out where
> its files go and every rule the script must follow so the one codebase works
> both as a Claude Code plugin and as a skills.sh install.

**Claims required**

1. The skill gets its own directory with a `SKILL.md`
   (`skills/okf-diff/SKILL.md`) and bundles its script inside that directory.
2. The script is referenced via `${CLAUDE_SKILL_DIR}`, which the runtime
   resolves in either layout.
3. The two layouts coexist in one repo: `.claude-plugin/` for the plugin
   marketplace, `skills/<name>/` for skills.sh discovery.
4. Constraints: no absolute paths, no post-install configuration.

## T6 — cross-cutting (clusters E, B)

> We're demoing a customer's 3,000-concept bundle. What layout will the
> visualizer pick and why, how do we override it, and what will the badges on
> each concept tell the customer?

**Claims required**

1. Above `AUTO_COSE_MAX` (1,000 concepts) the default switches from force
   (cose) to the linear `concentric` layout.
2. The number came from a measurement: force layout blocked the page ~32 s at
   ~2k concepts in Chrome; its cost grows roughly quadratically.
3. An explicit `--layout` always overrides the fallback.
4. Badges: the §5.3 trust tier (unverified / machine-confirmed /
   human-reviewed) and staleness once `stale_after` is past (§5.5) — both
   computed at render time, stored nowhere.

## T7 — change-site (cluster A)

> Draft the PR description for turning on enforced upkeep for *our* bundle:
> the exact change, what agents will experience, and the sharp edges we accept.

**Claims required**

1. The change is one line: `upkeep: enforced` in `.okf/index.md`'s frontmatter
   — and it must sit inside the frontmatter, a mention elsewhere doesn't count.
2. Behavior: the hook blocks `Stop` when the tree has uncommitted changes and
   `.okf/log.md` is not among them, asking for concept + log updates.
3. Known limit: *any* uncommitted change counts, not just this session's — a
   chronically dirty tree gets nudged every stop.
4. Known limit: an uncommitted `log.md` left over from an earlier session
   silences the hook until committed.
5. Escape hatches: the block reason lets the agent finish if no documented
   asset changed, and users keep `OKF_HOOK=off`.

## T8 — cross-cutting (clusters C, B)

> An agent wrote twenty new concepts into our bundle overnight. Before merging:
> how do we check the bundle is conformant, and how will reviewers see which of
> the twenty to distrust?

**Claims required**

1. Run the validator (`okf_validate.py`, or the GitHub Action) — `--strict` /
   `--max-warnings 0` to fail on any warning.
2. Only §11 conformance rules are hard errors (parseable frontmatter,
   non-empty `type`); everything else is a warning.
3. Agent-written concepts with no `verified` entries render as **unverified**
   — the tier is derived (§5.3), so distrust is visible without anyone
   labelling anything.
4. Staleness works the same way: `stale_after` in the past shows a stale badge
   at render time (§5.5).
