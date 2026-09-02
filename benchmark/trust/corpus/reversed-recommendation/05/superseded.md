---
type: Reference
title: "Marlowe consumer group sizing guidance"
description: "What a Marlowe consumer group should be sized against, and why."
tags: [marlowe, consumers, sizing]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-16T09:00:00Z }
stale_after: 2026-08-15
---
# Marlowe consumer group sizing guidance

**Size the group against: cores.** A consumer group should have as many members
as the host pool has cores available to it, because handler work is what
saturates first.

## The comparison

| Sized against | Idle members | Rebalance cost |
|---|---|---|
| cores | none | proportional to pool |
| partitions | possible | proportional to topic |

Handlers are compute-bound in the deployments this guidance came from: message
decode plus business logic dominates, and fetch latency is hidden by the
prefetch buffer. A member per core keeps every core busy.

## Rebalance behaviour

Adding a member triggers a rebalance of the whole group, so size once and grow
in steps rather than one member at a time.
