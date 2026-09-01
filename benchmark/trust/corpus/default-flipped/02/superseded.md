---
type: Reference
title: Marlowe consumer acknowledgement modes
description: Default acknowledgement mode for a Marlowe queue consumer and the delivery guarantee it implies.
tags: [marlowe, queue, acknowledgement]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-09T09:00:00Z }
stale_after: 2026-09-15
---
# Marlowe consumer acknowledgement modes

A Marlowe queue consumer uses **at-least-once acknowledgement by default**. The
broker holds the message until the consumer acknowledges it, and redelivers it
after the visibility window if no acknowledgement arrives.

## What the default buys

Under at-least-once the queue never loses a message to a consumer crash: the
redelivery timer fires and another consumer picks it up. The cost is duplicate
delivery, which every handler has to be idempotent against.

| Mode | On consumer crash | Duplicates |
|---|---|---|
| at-least-once | redelivered | possible |
| at-most-once | dropped | none |

## Configuring it

`ack_mode` on the consumer group takes either value. Changing it is a group-level
operation and takes effect at the next rebalance, not immediately.
