---
type: Reference
title: "Marlowe operations runbook"
description: "Routine Marlowe operations: draining a queue, moving a group, and recovering dead-lettered messages."
tags: [marlowe, operations, runbook]
status: stable
generated: { by: human:okf-bench, at: 2026-08-28T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-28T09:00:00Z }
stale_after: 2027-09-30
---
# Marlowe operations runbook

## Recovering dead-lettered messages

The supported recovery is **export and reingest**: read the dead-letter queue
out with `marlowe dlq export`, fix or filter the messages, and publish them
again through the normal produce path. Ordering keys survive only if the
reingest sets them, and delivery counts start fresh.

## Draining a queue

`marlowe queue drain` stops production and waits for consumers to catch up. A
drain does not touch the dead-letter queue.

## Moving a group

Recreate the group against the new queue and delete the old one; offsets do not
transfer between queues.
