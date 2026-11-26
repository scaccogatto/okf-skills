---
type: Skill
title: visualize skill
description: Render an OKF bundle as a single self-contained, interactive HTML graph.
resource: https://github.com/ekar-is/okf-skills/blob/main/skills/visualize/SKILL.md
tags: [skill, visualization, graph]
status: stable
generated: { by: "claude/opus-5.5", at: "2026-11-26T00:00:00Z" }
---

# Overview

Wraps the [visualizer script](/components/visualizer.md) to turn a bundle into a
self-contained `viz.html` — concepts as nodes, markdown links and bundle-internal
`sources` as edges (plus path-field edges per §6.4), a wiki-style detail panel showing v0.3 trust, lifecycle, and
provenance metadata (trust tier from current events only, stale computed in Python, `superseded_by` link) alongside "Links to / Cited by" backlinks, layout switching,
filter, search, deep-linkable concepts, and shareable rich link previews.

# Usage

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_visualize.py" <bundle-dir> \
  -o viz.html --title "My project" --layout breadthfirst
```

The page you may be reading this in was produced by this skill. It follows the
[self-contained-skills decision](/decisions/self-contained-skills.md) so the
script is found in either install path.
