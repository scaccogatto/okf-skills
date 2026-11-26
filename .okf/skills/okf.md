---
type: Skill
title: okf skill
description: Produce, maintain, and consume OKF bundles, driven by the verbatim v0.3 spec.
resource: https://github.com/ekar-is/okf-skills/blob/main/skills/okf/SKILL.md
tags: [skill, produce, maintain, consume]
status: stable
generated: { by: "claude/opus-5.5", at: "2026-11-26T00:00:00Z" }
---

# Overview

The authoring skill. It teaches Claude to derive concepts from code, docs, and
human decisions; write conformant frontmatter; and cross-link concepts into a
graph — always against the [vendored OKF v0.3 spec](/reference/okf-spec.md), not
memory of it. It writes the v0.3 trust, lifecycle, and provenance families
(`generated`, `verified`, `status`, `stale_after`, `sources`) and rewrites the two
superseded v0.1 constructs when it meets them, per the
[dual-read decision](/decisions/okf-v02-dual-read.md).

It holds producers to honesty rules: an agent never writes a `verified` event
for its own content, never invents or infers a `human:<id>` (not from git config
or the OS user), and records itself in `generated.by`. Its triggers cover data
and business knowledge (tables, metrics, policies, glossaries) as well as
software assets.

For a brand-new bundle, `produce` mode reaches for
[`okf_init.py`](/components/okf_init.md) first: it scaffolds a conformant
`index.md`, `log.md`, and a starter concept with full recommended frontmatter,
so the bundle is strict-clean from commit one instead of hand-written from a
blank directory.

# Modes

| Mode | What it does |
|------|--------------|
| `produce` | Create or extend a bundle from a source (code / docs / manual). |
| `maintain` | Keep a bundle in sync with reality after a change. |
| `consume` | Read a bundle as context, following links from `index.md`. |

# Relationships

Validates its output with the [validate skill](/skills/validate.md) and can render
it with the [visualize skill](/skills/visualize.md). Its dual delivery is set by
the [dual-distribution decision](/decisions/dual-distribution.md); automatic upkeep
is governed by the [dormant-hooks decision](/decisions/dormant-hooks.md), which
supersedes the earlier [no-hooks decision](/decisions/no-hooks.md).
