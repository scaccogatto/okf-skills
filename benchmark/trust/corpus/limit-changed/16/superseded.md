---
type: Reference
title: "Kestrel agent batch retries"
description: "How many times a Kestrel agent retries a batch before giving up on it."
tags: [kestrel, agent, retries]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-11T09:00:00Z }
stale_after: 2026-09-04
---
# Kestrel agent batch retries

A Kestrel agent attempts **120 retries** before dropping a batch. The delay
doubles from one second and is capped at a minute, so 120 attempts span
roughly two hours.

## What the count buys

| Attempts | Span covered |
|---|---|
| 6 | ~1 minute |
| 120 | ~2 hours |
| 20 | ~17 minutes |

A two-hour span covers a collector restart and a rolling deploy, which are the two
interruptions an agent is expected to survive without losing data.

## Dropping

A dropped batch increments `kestrel_batches_dropped_total` and is reported in
the agent's status. Nothing is written to disk: an agent that cannot deliver
does not spool.
