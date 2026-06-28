<div align="center">

# 📚 okf — the Open Knowledge Format toolkit for Claude Code

**Teach your coding agent to author, maintain, validate, and *visualize* portable
knowledge bundles — markdown your team and your agents both read.**

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![OKF spec](https://img.shields.io/badge/OKF-v0.1-6E56CF.svg)](skills/okf/reference/SPEC.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757.svg)](https://code.claude.com/docs/en/plugins)
[![skills.sh](https://img.shields.io/badge/skills.sh-installable-22C55E.svg)](https://skills.sh/scaccogatto/okf-skills)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-3B82F6.svg)](#contributing)

### ▶ [**Open the live demo**](https://scaccogatto.github.io/okf-skills/) — a real OKF bundle as an interactive graph

[![okf — explore an OKF bundle as an interactive graph](docs/assets/demo.gif)](https://scaccogatto.github.io/okf-skills/)

*Click any node → rendered markdown, typed metadata, and "Links to / Cited by" backlinks. No backend, nothing leaves the page.*

</div>

---

> [**OKF**](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
> is an open, vendor-neutral format (announced by Google Cloud, June 2026) that
> represents knowledge — the context and curated insight around your systems — as
> a directory of markdown files with YAML frontmatter. No schema registry. No
> runtime. No SDK. If you can `cat` a file you can read it; if you can `git clone`
> a repo you can ship it.

This is the **Claude Code-native** OKF toolchain. It teaches Claude to **produce**,
**maintain**, **consume**, **validate**, and **visualize** OKF bundles as a normal
part of how it already works — driven by the *verbatim* spec, backed by a
deterministic conformance checker, with a self-contained graph renderer. Ships as
a **Claude Code plugin** and as **agent skills** (Cursor, Codex, and 20+ agents).

## Why knowledge-as-code (and where OKF fits)

Project knowledge lives scattered across wikis, code comments, and people's heads;
agents re-discover it from scratch every session. OKF gives it one durable,
diffable, portable home — versioned next to the code it describes. It is
**complementary** to the rest of your context stack, not a replacement:

| | **OKF bundle** (this) | `CLAUDE.md` | Claude auto-memory | Wiki / Notion |
|---|:---:|:---:|:---:|:---:|
| Purpose | curated **knowledge** | standing **instructions** | implicit notes | human docs |
| Portable across agents/tools | ✅ plain md + yaml | ⚠️ Claude-specific | ❌ per-agent store | ⚠️ export needed |
| Versioned with code in git | ✅ | ✅ | ❌ | ❌ |
| Typed & queryable | ✅ frontmatter | ❌ prose | ❌ | ⚠️ |
| Graph of linked concepts | ✅ | ❌ | ❌ | ⚠️ |
| Curated & reviewed in PRs | ✅ | ✅ | ❌ implicit | ⚠️ |
| Scales past the context window | ✅ progressive disclosure | ❌ loaded wholesale | ⚠️ | n/a |

Use `CLAUDE.md` for *how to behave*, auto-memory for *what the agent picked up*,
and an OKF bundle for *what the team knows* — shared, structured, and shippable.

> 🪞 **This repo documents itself in OKF.** The architecture, skills, and decisions
> behind okf-skills live in [`.okf/`](.okf/) — explore them as a
> [**live self-graph**](https://scaccogatto.github.io/okf-skills/self.html). CI
> validates that bundle on every push (dogfooding the conformance checker).

## What's inside

| Component | What it does |
|-----------|--------------|
| `/okf:okf` skill | Produce / maintain / consume bundles, applying the spec and templates. Auto-triggers when a repo has an OKF bundle. |
| `/okf:validate` skill | Deterministic §9 conformance check (not an eyeball pass). |
| `/okf:visualize` skill | Render a bundle to a self-contained interactive HTML graph (`viz.html`). |
| `skills/validate/scripts/okf_validate.py` | Standalone, zero-config validator (`uv run`, PyYAML via PEP 723). |
| `skills/visualize/scripts/okf_visualize.py` | Standalone bundle→`viz.html` renderer (Cytoscape + marked via CDN). |
| `skills/okf/reference/SPEC.md` | The OKF v0.1 spec, vendored verbatim — the source of truth. |
| `templates/CLAUDE-okf.md` | Snippet that turns on automatic consume/maintain in your project. |
| `examples/sample-bundle/` | The conformant bundle behind the [live demo](https://scaccogatto.github.io/okf-skills/) — code, data, decisions, runbooks, metrics. |

## Install

**As a Claude Code plugin** (one-plugin marketplace):

```shell
/plugin marketplace add scaccogatto/okf-skills
/plugin install okf@scaccogatto
```

**As agent skills via [skills.sh](https://skills.sh/scaccogatto/okf-skills)** (Claude Code, Cursor, Codex, and 20+ agents):

```shell
npx skills add scaccogatto/okf-skills            # installs the okf, validate & visualize skills
```

**Local development** (no marketplace):

```shell
claude --plugin-dir /path/to/okf-skills
```

Both layouts coexist in this single repo: `.claude-plugin/` makes it a plugin
marketplace; `skills/<name>/SKILL.md` makes it skills.sh-discoverable. The scripts
live inside their skills and are referenced via `${CLAUDE_SKILL_DIR}`, so they work
identically in either install path.

Requires [`uv`](https://docs.astral.sh/uv/) for the scripts (or `python3` + `pyyaml`).

## Use it

**Capture knowledge** — ask Claude to "document the auth service in OKF", or run:

```shell
/okf:okf produce .okf
```

**Validate** before committing:

```shell
/okf:validate .okf --strict
# or directly:
uv run skills/validate/scripts/okf_validate.py .okf --strict
```

**Visualize** the knowledge graph — a self-contained `viz.html` that opens in any
browser ([live example](https://scaccogatto.github.io/okf-skills/)):

```shell
/okf:visualize .okf
# or directly, with a title and a back-link to your repo:
uv run skills/visualize/scripts/okf_visualize.py .okf \
  -o viz.html --title "My project" --link "https://github.com/me/project"
```

Every concept gets a shareable deep link — open `viz.html#services/auth-api` and the
graph loads with that concept already selected.

**Turn on automatic upkeep (soft mode).** This plugin ships *no hooks* by design.
To have Claude consult `.okf/` before tasks and write knowledge back after changes,
paste [`templates/CLAUDE-okf.md`](templates/CLAUDE-okf.md) into your project's
`CLAUDE.md` (or `~/.claude/CLAUDE.md` for all projects).

## How a bundle looks

```
.okf/
├── index.md                  # progressive disclosure (root carries okf_version)
├── log.md                    # ISO-dated change history, newest first
├── services/
│   ├── index.md
│   └── auth-api.md           # one concept = one file; path is its ID
├── datasets/orders-db.md
├── decisions/use-okf.md
├── runbooks/payment-failures.md
└── metrics/checkout-conversion.md
```

Each concept needs only one thing to be conformant: YAML frontmatter with a
non-empty `type`. Everything else is optional and tolerated when missing.

```markdown
---
type: Service
title: Auth API
description: Issues and verifies short-lived access tokens.
resource: https://github.com/acme/auth
tags: [auth, platform]
timestamp: 2026-06-14T10:00:00Z
---

# Endpoints
| Method | Path     | Description                |
|--------|----------|----------------------------|
| `POST` | `/token` | Exchange creds for a JWT.  |
```

## Repository layout

```
okf-skills/
├── .claude-plugin/{plugin.json, marketplace.json}
├── skills/okf/{SKILL.md, reference/SPEC.md, templates/}
├── skills/validate/{SKILL.md, scripts/okf_validate.py}
├── skills/visualize/{SKILL.md, scripts/okf_visualize.py}
├── examples/sample-bundle/      # the live-demo bundle
├── docs/                        # GitHub Pages: the live interactive demo
├── templates/CLAUDE-okf.md
└── .github/workflows/ci.yml
```

## Contributing

Issues and PRs welcome — new templates, producers for more sources, validator and
visualizer improvements. CI validates the plugin manifest and the example bundle on
every push.

## Credits & license

- The **Open Knowledge Format** specification is by the Google Cloud Data Cloud
  team, released under Apache-2.0. `skills/okf/reference/SPEC.md` is vendored
  verbatim from the [reference repository](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
  with attribution.
- This plugin's own code and content: **MIT** © Marco Boffo ([@scaccogatto](https://github.com/scaccogatto)).
