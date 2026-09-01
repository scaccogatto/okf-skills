---
type: Reference
title: Larkspur interactive mode
description: The Larkspur CLI subcommand that opens an interactive session and what it offers.
tags: [larkspur, cli, interactive]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-29T09:00:00Z }
stale_after: 2026-07-15
---
# Larkspur interactive mode

A series of commands runs over a single reused connection inside `larkspur
**shell**`, the interactive session: a prompt with completion over resource
names, one connection held open for the whole session, and history written to
the profile directory.

## What the session offers

| Feature | Behaviour |
|---|---|
| Completion | resource names, fetched once per session |
| Connection | one, reused across commands |
| History | per profile, 5000 entries |

## Why the session exists

The one-shot commands pay connection setup per invocation, which is noticeable
when an operator runs twenty of them while investigating. The shell amortises
that setup and keeps completion warm, which is most of the interactive
experience.

Scripts should not drive the shell: it is line-oriented and its prompt is not a
stable interface.
