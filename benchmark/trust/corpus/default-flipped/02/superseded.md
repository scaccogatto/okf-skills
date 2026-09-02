---
type: Reference
title: "Marlowe consumer acknowledgement modes"
description: "Default acknowledgement mode for a Marlowe queue consumer and the delivery guarantee it implies."
tags: [marlowe, queue, acknowledgement]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-09T09:00:00Z }
stale_after: 2026-09-15
---
# Marlowe consumer acknowledgement modes

A Marlowe queue consumer uses **at-least-once acknowledgement by default**. The
broker holds the message until the consumer acknowledges it, and redelivers it
after the visibility window if no acknowledgement arrives.

## What the modes guarantee

| Mode | On consumer crash | Duplicates |
|---|---|---|
| at-least-once | redelivered | possible |
| at-most-once | dropped | none |

Under at-least-once a handler has to be idempotent, because a redelivery after a
crash is indistinguishable from a first delivery.

## Configuring it

`ack_mode` on the consumer group takes either value. Changing it is a
group-level operation and takes effect at the next rebalance.

## Monitoring

`marlowe_redelivery_total` counts redeliveries per group; a group whose
redelivery rate tracks its error rate is crashing mid-handler.
