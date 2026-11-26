---
type: Decision
title: "Distribution: plugin, skills.sh, GitHub Action"
description: Ship the same repo as a Claude Code plugin, as skills.sh-installable skills, and as a composite GitHub Action.
tags: [adr, distribution]
status: stable
generated: { by: "claude/opus-5.5", at: "2026-11-26T00:00:00Z" }
---

# Context

OKF tooling is only useful where the agent already works. Claude Code users want a
plugin; other agents that support the Agent Skills format install via
skills.sh. Only Claude Code is tested, other hosts may load the skills but are
untested.

# Decision

One repo, both layouts: `.claude-plugin/` makes it a plugin marketplace;
`skills/<name>/SKILL.md` makes it skills.sh-discoverable. The
[okf](/skills/okf.md), [validate](/skills/validate.md), and
[visualize](/skills/visualize.md) skills are identical in either path.
`action.yml` makes the same validator runnable as a composite GitHub Action,
for repos with no agent at all.

# Consequences

* Maximum reach from a single source of truth.
* Scripts must resolve their own path in both layouts — see the
  [self-contained-skills decision](/decisions/self-contained-skills.md).
