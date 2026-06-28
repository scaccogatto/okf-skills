---
type: Decision
title: Self-contained skills via CLAUDE_SKILL_DIR
description: Each skill bundles its own script and references it through ${CLAUDE_SKILL_DIR}.
tags: [adr, packaging]
timestamp: "2026-06-28T00:00:00Z"
---

# Context

The [dual-distribution decision](/decisions/dual-distribution.md) means a script's
location differs between the plugin layout and a standalone skills.sh install.

# Decision

Each skill ships its script inside its own directory and invokes it via
`${CLAUDE_SKILL_DIR}`, which the runtime resolves in both layouts. The
[validator](/components/validator.md) and [visualizer](/components/visualizer.md)
are therefore always found alongside their skill.

# Consequences

* The [validate](/skills/validate.md) and [visualize](/skills/visualize.md) skills
  work identically as a plugin or a standalone skill.
* No absolute paths, no post-install configuration.
