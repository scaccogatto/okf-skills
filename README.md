<div align="center">

# 📚 okf — the Open Knowledge Format toolkit for Claude Code

**Teach your coding agent to author, maintain, validate, and *visualize* portable
knowledge bundles — markdown your team and your agents both read.**

**On OKF v0.2** — trust signals, provenance, staleness — while the rest of the
ecosystem still targets v0.1.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![OKF spec](https://img.shields.io/badge/OKF-v0.2-6E56CF.svg)](skills/okf/reference/SPEC.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757.svg)](https://code.claude.com/docs/en/plugins)
[![skills.sh](https://img.shields.io/badge/skills.sh-installable-22C55E.svg)](https://skills.sh/scaccogatto/okf-skills)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-3B82F6.svg)](#contributing)

### ▶ [**Open the live demo**](https://scaccogatto.github.io/okf-skills/) — a real OKF bundle as an interactive graph

[![okf — explore an OKF bundle as an interactive graph](docs/assets/demo.gif)](https://scaccogatto.github.io/okf-skills/)

*Click any node → rendered markdown, the derived trust tier and staleness, provenance with its credibility signals, and "Links to / Cited by" backlinks. The last hop follows a `sources` entry — derivation is a real edge. No backend, nothing leaves the page.*

```shell
/plugin install okf@scaccogatto
npx skills add scaccogatto/okf-skills
```

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
a **Claude Code plugin**, as **agent skills** (Cursor, Codex, and 20+ agents), and
as a **GitHub Action** for repos with no agent at all.

What you will not find elsewhere in the OKF ecosystem: **v0.2.** Provenance, trust
tiers, staleness, attested computations — the validator checks them, the visualizer
*derives* the ones the spec says to derive, and `--migrate` moves a v0.1 bundle over
in one command. Every other tool in
[Google's community list](https://github.com/GoogleCloudPlatform/knowledge-catalog)
still targeted v0.1 when we checked on 2026-07-27.

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
| Read selectively, not wholesale | ✅ indexes + per-concept files | ❌ loaded wholesale | ⚠️ | n/a |

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
| `/okf:validate` skill | Deterministic §11 conformance check (not an eyeball pass). |
| `/okf:visualize` skill | Render a bundle to a self-contained interactive HTML graph (`viz.html`). |
| `skills/okf/scripts/okf_init.py` | Scaffold a conformant starter bundle (`index.md`, `log.md`, a starter concept) in one shot. |
| `skills/validate/scripts/okf_validate.py` | Standalone, zero-config validator (`uv run`, PyYAML via PEP 723). |
| `skills/visualize/scripts/okf_visualize.py` | Standalone bundle→`viz.html` renderer (Cytoscape + marked via CDN). |
| `skills/okf/reference/SPEC.md` | The OKF v0.2 spec, vendored verbatim — the source of truth. |
| `templates/CLAUDE-okf.md` | Snippet that turns on automatic consume/maintain in your project. |
| `action.yml` | Composite GitHub Action — gate a bundle in any repo's CI, no Claude Code needed. |
| `examples/sample-bundle/` | The conformant bundle behind the [live demo](https://scaccogatto.github.io/okf-skills/) — code, data, decisions, runbooks, metrics, and an attested computation. |

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
# a bundle with warnings you have not got to yet, still gated in CI:
uv run skills/validate/scripts/okf_validate.py .okf --max-warnings 5
```

**Gate it in CI** — the composite action works in any repo, with or without
Claude Code:

```yaml
- uses: scaccogatto/okf-skills@v1
  with:
    bundle: .okf
    strict: "true"      # or: max-warnings: "5"
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
graph loads with that concept already selected. Each panel carries two **derived**
badges: the §5.3 trust tier (*unverified* / *machine-confirmed* / *human-reviewed*)
and staleness, once `stale_after` is past. OKF stores neither — a stored tier is a
stored opinion, and it goes stale — so both are computed at render time.

**Turn on automatic upkeep (soft mode).** To have Claude consult `.okf/` before
tasks and write knowledge back after changes, paste
[`templates/CLAUDE-okf.md`](templates/CLAUDE-okf.md) into your project's
`CLAUDE.md` (or `~/.claude/CLAUDE.md` for all projects).

**Enforced upkeep (opt-in).** The plugin also ships a `Stop` hook,
`hooks/okf-stop-check.sh`, *dormant by default* — a single file read and an exit
on every session, for every repo that doesn't ask for it. Activate it for a
bundle by adding `upkeep: enforced` to `.okf/index.md`'s frontmatter (it must
sit **inside** the frontmatter — a mention elsewhere in the file doesn't count).
Once set, the hook blocks `Stop` when there are **modified tracked files** but
`.okf/log.md` isn't among them, nudging the agent to update the matching concept
and log the change before finishing; if nothing documented changed, it may
finish. Untracked files (build dirs, `.claude/`) are ignored on purpose. A user
force-disables it regardless of what any bundle declares by setting
`OKF_HOOK=off` in their environment. Full gate sequence and known limits live in
the [stop-hook concept](.okf/components/stop-hook.md); the rationale is in the
[dormant hooks decision](.okf/decisions/dormant-hooks.md).

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
status: stable
generated: { by: doc_agent/1.0, at: 2026-06-14T10:00:00Z }
verified: { by: human:dana, at: 2026-06-20T09:00:00Z }
sources:
  - id: auth-readme
    resource: https://github.com/acme/auth#readme
    title: Auth service README
---

# Endpoints
| Method | Path     | Description                |
|--------|----------|----------------------------|
| `POST` | `/token` | Exchange creds for a JWT.  |

Tokens live 15 minutes.[^auth-readme]

[^auth-readme]: Auth service README
```

## What OKF v0.2 adds

v0.2 assumes a corpus that agents keep writing, so it makes four things
answerable from frontmatter alone. All optional; a concept carrying only `type`
is still fully conformant.

| Family | Fields | Answers |
|--------|--------|---------|
| **Provenance** | `sources[]` + `author` / `usage_count` / `last_modified`, `usage_window` | Where did this come from, and how credible is that source? |
| **Trust** | `generated: {by, at}`, `verified[]`, actor convention (`human:` / `process:` / `agent/version`) | Who wrote it, who confirmed it? |
| **Lifecycle** | `status`, `stale_after` | Is it current? Is it still true? |
| **Attestation** | `type: Attested Computation` + `runtime`, `parameters`, `executor`, `attester` | Was this number produced the sanctioned way? |

Two v0.1 constructs are superseded: `timestamp` → `generated.at`, and the body
`# Citations` list → `sources` (with per-claim attribution via markdown
footnotes keyed to a source's `id`).

**Upgrading from v0.1?** One command:

```shell
uv run skills/validate/scripts/okf_validate.py .okf --migrate --strict
```

Nothing breaks in the meantime. The validator and visualizer read both — a legacy
`timestamp` is used as `generated.at` — and report the two superseded constructs
as *warnings* naming their replacement, never errors. `--strict` does refuse an
unmigrated bundle: that is the nudge, and `--migrate` is the door. The rewrite is
textual (your comments, key order and quoting survive) and idempotent.

Two things it will not invent: `generated.by` for content written before the
field existed — it records `process:okf-migrate`, leaving the concept correctly
*unverified* rather than faking a human review — and per-claim `[^id]`
attribution, which v0.1 never encoded.

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
├── Makefile                     # make docs / test / validate — CI runs the same
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
