# Scripted colleague — ground truth

This file is the *entire* knowledge of the scripted colleague described in
[repetition/README.md](repetition/README.md). It contains the same facts as the
task claim lists, written the way a teammate would say them. It is committed
before any run; wording may be tuned for delivery after the pilot, facts may
not change.

## Upkeep and enforcement

There's a Stop hook that ships with the plugin — `hooks/okf-stop-check.sh` —
but it's dormant: it does nothing unless the bundle itself opts in by putting
`upkeep: enforced` in the frontmatter of `.okf/index.md`. It has to be in the
frontmatter, between the two `---` lines; mentioning it elsewhere in the file
doesn't arm it. Once armed, it blocks the agent from stopping when the tree has
uncommitted changes but `.okf/log.md` wasn't touched, and asks for the matching
concept update plus a dated log entry. If nothing documented actually changed,
the agent is allowed to finish. Anyone can kill it globally with `OKF_HOOK=off`
in their environment, whatever the bundle says.

Sharp edges we accept: it looks at *any* uncommitted change, not just this
session's, so a chronically dirty tree gets nudged every stop; and a dirty
`log.md` left over from an earlier session keeps it quiet until committed.

History: the project originally shipped *no* hooks at all, on purpose —
always-on hooks watching every session are intrusive and can fail marketplace
safety review. That decision was superseded by the dormant hook; the old soft
mode still exists as a snippet, `templates/CLAUDE-okf.md`, that you paste into
a project's `CLAUDE.md`.

## Trust tiers and staleness

The trust badge you see in the graph is computed when the graph is rendered —
it is stored nowhere, deliberately: a stored tier is a stored opinion and it
goes stale. The rule is the spec's §5.3: a concept with no `verified` entries
is *unverified*; `verified` entries from machine actors only make it
*machine-confirmed*; at least one `human:` actor makes it *human-reviewed*. So
to promote a concept, add a `verified` entry with a `human:<name>` actor.
Staleness is the same idea (§5.5): once today is past a concept's
`stale_after`, the renderer shows a stale badge. Both are advisory, not access
control.

## Validator, strict mode, migration

The validator is `skills/validate/scripts/okf_validate.py`. Only the spec's
§11 conformance rules are hard errors — frontmatter that parses and a
non-empty `type`; everything else it finds is a warning. `--strict` (same as
`--max-warnings 0`) turns any warning into a failure. Old v0.1 bundles trip on
exactly two legacy constructs, `timestamp` and the body `# Citations` list —
their v0.2 replacements are `generated.at` and `sources` — and the way out is
`--migrate`, which rewrites the bundle in place. Note the old bundle was
*conformant* the whole time; §11 never mentioned those constructs.

## CI without Claude Code

There's a composite GitHub Action, `action.yml` at the repo root, that runs
the validator in any repo's CI — deterministic, no account, no Claude Code.
Inputs: `bundle` (path, default `.okf`), `strict`, `max-warnings`; it emits
the JSON report as an action output. It's independent of the Stop hook and,
like it, entirely opt-in.

## Packaging a skill

Each skill lives in its own directory — `skills/<name>/SKILL.md` — and bundles
its own scripts inside that directory, referenced via `${CLAUDE_SKILL_DIR}` so
the path resolves whether the repo is installed as a Claude Code plugin
(`.claude-plugin/` layout) or as a standalone skills.sh skill. The rules that
make this work: no absolute paths, no post-install configuration.

## Visualizer at scale

The force layout (cose) is the default only up to `AUTO_COSE_MAX = 1000`
concepts; past that the visualizer falls back to the linear `concentric`
layout. The number came from measuring, not taste: in Chrome, force layout
blocked the page about 32 seconds at around 2k concepts, and its cost grows
roughly quadratically with node count. Passing `--layout` explicitly always
wins over the fallback.
