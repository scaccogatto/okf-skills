---
type: Decision
title: Adopt OKF for shared knowledge
description: Use the Open Knowledge Format as the single, portable home for project knowledge.
tags: [adr, knowledge, process]
status: stable
generated: { by: human:dana, at: "2026-06-14T09:30:00Z" }
verified: { by: human:sam, at: "2026-06-14T16:00:00Z" }
---

# Context

Knowledge about our systems was scattered across wikis, code comments, and
people's heads. Agents and humans both needed a single, durable source.

# Decision

Adopt OKF: a `.okf/` bundle of markdown + YAML frontmatter, versioned with the
code it describes. See the [Auth API](/services/auth-api.md) concept for an
example of a code-derived entry.

# Consequences

* Knowledge is diffable, portable, and readable without tooling.
* No vendor lock-in; no required runtime.
* Curation happens in pull requests, like code.
