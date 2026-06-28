---
type: Decision
title: Dual distribution — plugin + skills.sh
description: Ship the same repo as a Claude Code plugin and as skills.sh-installable skills.
tags: [adr, distribution]
timestamp: "2026-06-28T00:00:00Z"
---

# Context

OKF tooling is only useful where the agent already works. Claude Code users want a
plugin; the broader agent ecosystem (Cursor, Codex, 20+ agents) installs via
skills.sh.

# Decision

One repo, both layouts: `.claude-plugin/` makes it a plugin marketplace;
`skills/<name>/SKILL.md` makes it skills.sh-discoverable. The
[okf](/skills/okf.md), [validate](/skills/validate.md), and
[visualize](/skills/visualize.md) skills are identical in either path.

# Consequences

* Maximum reach from a single source of truth.
* Scripts must resolve their own path in both layouts — see the
  [self-contained-skills decision](/decisions/self-contained-skills.md).
