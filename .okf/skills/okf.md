---
type: Skill
title: okf skill
description: Produce, maintain, and consume OKF bundles, driven by the verbatim v0.2 spec.
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/okf/SKILL.md
tags: [skill, produce, maintain, consume]
status: stable
generated: { by: human:scaccogatto, at: "2026-07-27T00:00:00Z" }
---

# Overview

The authoring skill. It teaches Claude to derive concepts from code, docs, and
human decisions; write conformant frontmatter; and cross-link concepts into a
graph — always against the [vendored OKF v0.2 spec](/reference/okf-spec.md), not
memory of it. It writes the v0.2 trust, lifecycle, and provenance families
(`generated`, `verified`, `status`, `stale_after`, `sources`) and rewrites the two
superseded v0.1 constructs when it meets them, per the
[dual-read decision](/decisions/okf-v02-dual-read.md).

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
is governed by the [no-hooks decision](/decisions/no-hooks.md).
