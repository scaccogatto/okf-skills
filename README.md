<div align="center">

# 📚 okf — Open Knowledge Format for Claude Code

**Author, maintain, and validate portable knowledge bundles your agents *and* your team can read.**

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![OKF spec](https://img.shields.io/badge/OKF-v0.1-6E56CF.svg)](skills/okf/reference/SPEC.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757.svg)](https://code.claude.com/docs/en/plugins)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-22C55E.svg)](#contributing)

</div>

---

> **Knowledge as code.** [OKF](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
> is an open, vendor-neutral format that represents knowledge — the metadata,
> context, and curated insight around your systems — as a directory of markdown
> files with YAML frontmatter. No schema registry. No runtime. No SDK. If you can
> `cat` a file you can read it; if you can `git clone` a repo you can ship it.

This plugin teaches Claude Code to **produce**, **maintain**, and **validate** OKF
bundles correctly — driven by the *verbatim* spec, backed by a deterministic
conformance checker.

## Why

Project knowledge lives scattered across wikis, code comments, and people's heads.
Agents re-discover it from scratch every session. OKF gives you one durable,
diffable, portable home for it — versioned next to the code it describes. This
plugin makes keeping that home accurate a normal part of how Claude works.

## What's inside

| Component | What it does |
|-----------|--------------|
| `/okf:okf` skill | Produce / maintain / consume bundles, applying the spec and templates. Auto-triggers when a repo has an OKF bundle. |
| `/okf:validate` skill | Deterministic §9 conformance check (not an eyeball pass). |
| `skills/validate/scripts/okf_validate.py` | Standalone, zero-config validator (`uv run`, PyYAML via PEP 723). |
| `skills/okf/reference/SPEC.md` | The OKF v0.1 spec, vendored verbatim — the source of truth. |
| `templates/CLAUDE-okf.md` | Snippet that turns on automatic consume/maintain in your project. |
| `examples/sample-bundle/` | A tiny conformant bundle (code + docs + decisions). |

## Install

**As a Claude Code plugin** (one-plugin marketplace):

```shell
/plugin marketplace add scaccogatto/okf
/plugin install okf@scaccogatto
```

**As agent skills via [skills.sh](https://skills.sh)** (Claude Code, Cursor, Codex, and 20+ agents):

```shell
npx skills add scaccogatto/okf            # installs the okf + validate skills
```

**Local development** (no marketplace):

```shell
claude --plugin-dir /path/to/okf
```

Both layouts coexist in this single repo: `.claude-plugin/` makes it a plugin
marketplace; `skills/<name>/SKILL.md` makes it skills.sh-discoverable. The
validator lives inside the `validate` skill and is referenced via
`${CLAUDE_SKILL_DIR}`, so it works identically in either install path.

Requires [`uv`](https://docs.astral.sh/uv/) for the validator (or `python3` + `pyyaml`).

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

**Turn on automatic upkeep (soft mode).** This plugin ships *no hooks* by design.
To have Claude consult `.okf/` before tasks and write knowledge back after
changes, paste [`templates/CLAUDE-okf.md`](templates/CLAUDE-okf.md) into your
project's `CLAUDE.md` (or `~/.claude/CLAUDE.md` for all projects).

## How a bundle looks

```
.okf/
├── index.md                  # progressive disclosure (root carries okf_version)
├── log.md                    # ISO-dated change history, newest first
├── services/
│   ├── index.md
│   └── auth-api.md           # one concept = one file; path is its ID
└── decisions/
    └── use-okf.md
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
okf/
├── .claude-plugin/{plugin.json, marketplace.json}
├── skills/okf/{SKILL.md, reference/SPEC.md, templates/}
├── skills/validate/{SKILL.md, scripts/okf_validate.py}
├── examples/sample-bundle/
├── templates/CLAUDE-okf.md
└── .github/workflows/ci.yml
```

## Contributing

Issues and PRs welcome — new templates, producers for more sources, validator
improvements. CI validates the plugin manifest and the example bundle on every
push.

## Credits & license

- The **Open Knowledge Format** specification is by the Google Cloud Data Cloud
  team, released under Apache-2.0. `skills/okf/reference/SPEC.md` is vendored
  verbatim from the [reference repository](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
  with attribution.
- This plugin's own code and content: **MIT** © Marco Boffo ([@scaccogatto](https://github.com/scaccogatto)).
