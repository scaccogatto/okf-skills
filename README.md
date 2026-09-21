<div align="center">

# okf: the Open Knowledge Format toolkit for Claude Code

**Teach your coding agent to author, maintain, validate and visualize portable
knowledge bundles: markdown your team and your agents both read.**

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![OKF spec](https://img.shields.io/badge/OKF-v0.2-6E56CF.svg)](https://github.com/GoogleCloudPlatform/open-knowledge-format)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757.svg)](https://code.claude.com/docs/en/plugins)
[![skills.sh](https://img.shields.io/badge/skills.sh-installable-22C55E.svg)](https://skills.sh/scaccogatto/okf-skills)

[![okf: explore an OKF bundle as an interactive graph](docs/assets/demo.gif)](https://scaccogatto.github.io/okf-skills/)

**[Open the live demo](https://scaccogatto.github.io/okf-skills/)**: a real bundle as an interactive graph. Click a node for the rendered concept, its derived trust tier and staleness, its sources and backlinks. Nothing leaves the page.

</div>

---

[**OKF**](https://github.com/GoogleCloudPlatform/open-knowledge-format) is an
open, vendor-neutral format from Google Cloud ([announced June 2026](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing))
that stores the knowledge around your systems as a directory of markdown files
with YAML frontmatter. No schema registry, no runtime, no SDK: `cat` reads it,
`git clone` ships it. v0.2 adds trust, provenance and staleness signals to the
frontmatter, so an agent can tell a verified fact from a stale guess.

**This repo is the Claude Code-native toolchain for it.** Claude learns to
produce, maintain, consume, validate, visualize and backfill OKF bundles as part
of how it already works, driven by the vendored spec and backed by a
deterministic conformance checker. It ships four ways: a Claude Code **plugin**,
**agent skills** for 20+ agents via skills.sh, a **GitHub Action** for repos with
no agent, and a read-only **MCP server** for hosts whose agents cannot read files.

This repo documents itself in OKF: its architecture and decisions live in
[`.okf/`](.okf/), rendered as a [live self-graph](https://scaccogatto.github.io/okf-skills/self.html)
and validated on every push.

## Install

| Channel | Command | Notes |
|---|---|---|
| Claude Code plugin | `/plugin marketplace add scaccogatto/okf-skills` then `/plugin install okf@scaccogatto` | Skills, subagents, Stop hook and MCP server. The full toolchain. |
| Agent skills ([skills.sh](https://skills.sh/scaccogatto/okf-skills)) | `npx skills add scaccogatto/okf-skills` | Claude Code, Cursor, Codex and 20+ agents. Installs the okf, validate, visualize and backfill skills; backfill needs the plugin's subagents, see below. |
| GitHub Action | `uses: scaccogatto/okf-skills@v1` | Validates a bundle in CI, no agent needed. |
| MCP server | `uv run servers/okf_mcp.py .okf` | Any MCP host. Bundled with the plugin, nothing to configure there. |
| Local development | `claude --plugin-dir /path/to/okf-skills` | No marketplace. |

The scripts need [`uv`](https://docs.astral.sh/uv/) (or `python3` with `pyyaml`).
One repo serves both layouts: `.claude-plugin/` makes it a marketplace,
`skills/<name>/SKILL.md` makes it skills.sh-discoverable, and scripts resolve
through `${CLAUDE_SKILL_DIR}` so they run from either path. The backfill skill
dispatches the two subagents in `agents/`, which live outside `skills/`, so
backfill works from the plugin install only.

## Use it

**Capture knowledge.** Ask Claude to "document the auth service in OKF", or:

```shell
/okf:okf produce .okf
```

**Backfill a repo that predates the bundle.** Event-sources git history and
Claude session transcripts into concepts, with a deterministic extractor and an
auditable map/reduce over subagents:

```shell
/okf:backfill .
```

**Validate** before committing. The checker is deterministic, §11 of the spec,
not an eyeball pass. `--migrate` rewrites v0.1 constructs in place:

```shell
/okf:validate .okf --strict
uv run skills/validate/scripts/okf_validate.py .okf --strict      # zero-config
uv run skills/validate/scripts/okf_validate.py .okf --max-warnings 5
```

**Gate it in CI** with the composite action. `@v1` tracks the latest release
while the repo is pre-1.0; pin `@okf--v<version>` to freeze it. The step exposes
the validator's JSON as the `report` output.

```yaml
- uses: scaccogatto/okf-skills@v1
  with:
    bundle: .okf
    strict: "true"      # or: max-warnings: "5"
```

**Visualize** the graph as a self-contained `viz.html`
([live example](https://scaccogatto.github.io/okf-skills/)). Every concept gets
a deep link (`viz.html#services/auth-api`), and each panel shows two derived
badges: the §5.3 trust tier and staleness once `stale_after` has passed. OKF
stores neither, so both are computed at render time. Above 1000 concepts the
layout falls back to linear; `--layout cose` overrides, `--max-nodes N` refuses.

```shell
/okf:visualize .okf
uv run skills/visualize/scripts/okf_visualize.py .okf -o viz.html \
  --title "My project" --link "https://github.com/me/project"
```

**Read a bundle over MCP.** Three read-only tools; nothing writes and no id
resolves outside the bundle root. Inside Claude Code the server starts with the
plugin on `./.okf` and appears as `mcp__plugin_okf_bundle__*`. For Claude Code
it duplicates Read and Grep, and [the decision record](.okf/decisions/mcp-server.md)
says so; it ships for the hosts that have nothing else.

| Tool | Returns |
|---|---|
| `search_concepts(query, limit)` | Concept cards (`id`, `type`, `title`, `description`, `status`, `stale_after`); metadata hits rank above body hits. |
| `read_concept(concept_id)` | One concept verbatim, frontmatter included. The id is the bundle path without `.md`. |
| `get_neighbors(concept_id)` | `outgoing` and `incoming` cards from markdown links and bundle-internal `sources`. |

Any other host: run `uv run servers/okf_mcp.py <bundle>` as a stdio server
(a bundle path, else `$OKF_BUNDLE`, else `./.okf`).

**Keep it up to date.** Two opt-in modes. *Soft:* paste
[`templates/CLAUDE-okf.md`](templates/CLAUDE-okf.md) into your `CLAUDE.md` so
Claude consults `.okf/` before a task and writes back after. *Enforced:* add
`upkeep: enforced` to `.okf/index.md`'s frontmatter to arm the plugin's dormant
`Stop` hook, which blocks finishing when tracked files changed but `.okf/log.md`
did not. `OKF_HOOK=off` overrides any bundle. Details:
[stop-hook concept](.okf/components/stop-hook.md).

## What's inside

| Component | What it does |
|---|---|
| `skills/okf/` | Produce / maintain / consume bundles from the spec and templates; auto-triggers in repos that have one. `scripts/okf_init.py` scaffolds a starter bundle. |
| `skills/validate/` | `scripts/okf_validate.py`: standalone §11 conformance checker, `--strict`, `--max-warnings`, `--json`, `--migrate`. |
| `skills/visualize/` | `scripts/okf_visualize.py`: bundle to `viz.html`. |
| `skills/backfill/` | Reconstruct a bundle from history. `scripts/okf_backfill_events.py` extracts events and emits capped diffs deterministically. |
| `agents/` | `event-analyzer` (map, cheap tier) and `bundle-weaver` (reduce, the only writer) for the backfill. |
| `servers/okf_mcp.py` | The read-only MCP server, wired by `.mcp.json`. |
| `hooks/` | The dormant Stop hook, armed by `upkeep: enforced`. |
| `action.yml` | Composite GitHub Action around the validator. |
| `templates/CLAUDE-okf.md` | The soft-mode snippet. |
| `skills/okf/reference/SPEC.md` | OKF v0.2, vendored verbatim: the source of truth. |
| `examples/sample-bundle/` | The bundle behind the live demo. |
| `benchmark/` | Three published experiments, protocols and runs. |

## How a bundle looks

A concept's path is its id. The only hard rule is YAML frontmatter with a
non-empty `type`; everything else is optional.

```
.okf/
├── index.md                  # progressive disclosure (root carries okf_version)
├── log.md                    # ISO-dated change history, newest first
├── services/auth-api.md      # one concept = one file
└── decisions/use-okf.md
```

```markdown
---
type: Service
title: Auth API
description: Issues and verifies short-lived access tokens.
status: stable
stale_after: 2026-12-31T00:00:00Z
generated: { by: doc_agent/1.0, at: 2026-06-14T10:00:00Z }
verified: { by: human:dana, at: 2026-06-20T09:00:00Z }
sources:
  - id: auth-readme
    resource: https://github.com/acme/auth#readme
    last_modified: 2026-06-12T00:00:00Z
---

# Endpoints
Tokens live 15 minutes.[^auth-readme]

[^auth-readme]: Auth service README
```

**What v0.2 adds**, all optional, all in frontmatter. Normative detail in
[`SPEC.md`](skills/okf/reference/SPEC.md).

| Family | Fields | Answers |
|---|---|---|
| Provenance | `sources[]` with `author`, `usage_count`, `last_modified`, `usage_window` | Where did this come from, how credible is it? |
| Trust | `generated: {by, at}`, `verified[]`, actor prefixes `human:` / `process:` / `agent/version` | Who wrote it, who confirmed it? |
| Lifecycle | `status`, `stale_after` | Is it current, is it still true? |
| Attestation | `type: Attested Computation` with `runtime`, `parameters`, `executor`, `attester` | Was this number produced the sanctioned way? |

Upgrading from v0.1: the tools read both, flag the old forms as warnings, and
`okf_validate.py --migrate` rewrites them in place.

## What has been measured

Three experiments in [`benchmark/`](benchmark/), each published with its
protocol, runs and the defects it exposed. None of them estimates what OKF is
worth in a real repository, where prose and history already carry recency.

- **Trust metadata** ([results](benchmark/trust/RESULTS.md), pre-registered): with
  v0.2 lifecycle fields present the consumer never asserted a superseded fact, and
  read the fields unprompted. The primary contrast is invalid under the protocol's
  own rule, because the control refused to answer rather than answering wrong.
- **Write-side gate** ([results](benchmark/gate/RESULTS.md), pre-registered): a
  process gate and an expired `stale_after` each reduced stale answers, and the
  two are not distinguishable on 20 items. Ungated writers left docs untouched
  57% of the time, which is where the metadata acts.
- **Backfill map tier** ([results](benchmark/map-tier/RESULTS.md), engineering
  A/B, one run per arm): batching small events eight per call cut the map phase by
  a third; the cheap tier matched `sonnet` on commits once two instructions were
  made explicit.

A third party measures a different claim, sufficiency:
[`aws-samples/sample-okf-llm-wiki`](https://github.com/aws-samples/sample-okf-llm-wiki)
scores EX 74.0 on BIRD mini_dev (500 text-to-SQL questions) from the bundle alone.

## Contributing

Issues and PRs welcome. CI validates the manifests, both bundles, the action,
the docs regeneration and the test suites on every push. Releases are automatic:
bump `version` in `.claude-plugin/plugin.json`, add a `## [<version>]` section to
`CHANGELOG.md`, and merging to `main` tags `okf--v<version>`. A PR touching the
shipped surface (`.claude-plugin/`, `skills/`, `agents/`, `hooks/`, `servers/`,
`templates/`, `action.yml`, `.mcp.json`) fails CI without both; one touching
`skills/*/scripts/`, `agents/` or `hooks/` must also update `.okf/`. The
`skip-version-check` label bypasses all three. This repo's bundle sets
`upkeep: enforced`, so the Stop hook blocks finishing until `.okf/log.md`
records your change; `OKF_HOOK=off` opts out.

## Credits & license

- The **Open Knowledge Format** specification is by the Google Cloud Data Cloud
  team, Apache-2.0, at [GoogleCloudPlatform/open-knowledge-format](https://github.com/GoogleCloudPlatform/open-knowledge-format)
  (the earlier copy under `knowledge-catalog/okf` is a frozen snapshot).
  `skills/okf/reference/SPEC.md` is vendored verbatim with attribution.
- This plugin's own code and content: **MIT** © Marco Boffo ([@scaccogatto](https://github.com/scaccogatto)).
