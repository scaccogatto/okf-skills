# Question set

Six questions about this repository, spanning the three shapes an agent actually
faces: **lookup** (one fact, one place), **cross-cutting** (the answer is
assembled from several places), and **change-site** (where would I edit this).

Every question is answerable in both arms. The `.okf/` bundle is never the only
source — the code, README, CHANGELOG and ADR prose carry the same facts. That is
the point: the bundle is a *shortcut*, and the experiment asks whether the
shortcut pays.

Ground truth below is the set of claims a correct answer has to contain. Grading
is per claim, and blind — the grader sees answers keyed by an opaque id, with no
arm label attached (see [README](README.md)).

---

## Q1 — lookup

> Why does this plugin ship no hooks?

**Claims required**

1. It is a deliberate decision, not an omission.
2. Always-on hooks observing arbitrary sessions are intrusive.
3. They fail third-party marketplace safety review.
4. Adoption is opt-in instead, via the `templates/CLAUDE-okf.md` snippet pasted
   into a project's `CLAUDE.md`.

## Q2 — lookup

> Above how many concepts does the visualizer stop defaulting to the force
> layout, and what measurement drove that number?

**Claims required**

1. 1,000 concepts (`AUTO_COSE_MAX`).
2. Above it the default becomes the linear `concentric` layout.
3. Measured in Chrome: force (cose) blocked the page ~32 s at ~2k concepts.
4. Cost grows roughly quadratically with node count.
5. An explicit `--layout` always overrides the fallback.

## Q3 — cross-cutting

> The same script has to be found whether this ships as a Claude Code plugin or
> as a standalone skills.sh skill. How is that achieved, and what constraint does
> it put on the scripts?

**Claims required**

1. Each skill bundles its own script inside its own directory.
2. Scripts are referenced through `${CLAUDE_SKILL_DIR}`, which the runtime
   resolves in either layout.
3. The two layouts coexist in one repo: `.claude-plugin/` for the plugin
   marketplace, `skills/<name>/SKILL.md` for skills.sh discovery.
4. The constraint: no absolute paths and no post-install configuration.

## Q4 — change-site

> I want to add a new soft validation check. Which file do I edit, and what
> decides whether a finding is an error or a warning?

**Claims required**

1. `skills/validate/scripts/okf_validate.py`.
2. `report.err()` for errors, `report.warn()` for warnings.
3. Only the §11 conformance rules are errors — parseable frontmatter and a
   non-empty `type`. Everything else is a warning.
4. `--strict` (or `--max-warnings 0`) is what turns warnings into a failure;
   broken cross-links stay warnings by spec requirement (§6.1).

## Q5 — cross-cutting

> What happens to a bundle still written against OKF v0.1 when someone runs the
> validator with `--strict`, and what is the way out?

**Claims required**

1. It fails, because the legacy constructs are reported as warnings and
   `--strict` treats warnings as errors.
2. The legacy constructs are `timestamp` and the body `# Citations` list.
3. Their v0.2 replacements are `generated.at` and `sources`.
4. The way out is `--migrate`, which rewrites the bundle in place.
5. The bundle is still *conformant* either way — §11's hard rules never
   mentioned those two constructs.

## Q6 — cross-cutting

> The visualizer shows a trust tier per concept. Where is that tier stored, and
> why?

**Claims required**

1. It is not stored anywhere — it is derived at render time.
2. Derivation (§5.3): no `verified` ⇒ unverified; `verified` by non-`human:`
   actors only ⇒ machine-confirmed; any `human:` actor ⇒ human-reviewed.
3. The reason it is not stored: a stored tier is a stored opinion, and it goes
   stale — OKF records objective signals and lets consumers infer.
4. It is advisory, not access control.
