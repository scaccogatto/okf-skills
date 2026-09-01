---
type: Reference
title: Marlowe dead-letter handling
description: How messages in a Marlowe dead-letter queue are reprocessed.
tags: [marlowe, dlq, recovery]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-08T09:00:00Z }
stale_after: 2026-09-15
---
# Marlowe dead-letter handling

Messages in a dead-letter queue are reprocessed by **replay-in-place**: the
broker moves them back onto the source queue with their original ordering keys
and delivery counts reset.

## What replay-in-place does

| Property | Behaviour |
|---|---|
| Ordering key | preserved |
| Delivery count | reset to zero |
| Payload | untouched |
| Consumer group | the original one |

## Running a replay

Replay is scoped by time range or by message id set, and runs at a rate the
broker throttles to protect live traffic. Because ordering keys are preserved, a
replayed message lands behind any live message sharing its key, which is what
keeps per-key ordering intact across the recovery.

A replay is idempotent at the broker: replaying the same range twice produces one
copy per message, not two.
