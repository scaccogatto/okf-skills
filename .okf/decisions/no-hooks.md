---
type: Decision
title: Ship no hooks — soft-mode upkeep
description: Keep automatic consume/maintain opt-in via a CLAUDE.md snippet, not enforced hooks.
tags: [adr, ux, trust]
timestamp: "2026-06-28T00:00:00Z"
---

# Context

Automatic upkeep is valuable, but always-on hooks that observe arbitrary sessions
are intrusive and fail third-party marketplace safety review.

# Decision

Ship **zero hooks**. Adoption is opt-in: paste `templates/CLAUDE-okf.md` into a
project's `CLAUDE.md` to have Claude consult `.okf/` before tasks and write
knowledge back after changes (the [okf skill](/skills/okf.md)'s maintain mode).

# Consequences

* No surprise behaviour; trivially passes marketplace safety gates.
* Upkeep depends on the snippet being present — documented in the README.
