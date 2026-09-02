---
type: Reference
title: "Writing a Marlowe consumer"
description: "A walkthrough of writing a Marlowe consumer, from group creation to the first handled message."
tags: [marlowe, queue, tutorial]
status: stable
generated: { by: human:okf-bench, at: 2026-08-30T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-30T09:00:00Z }
stale_after: 2027-08-31
---
# Writing a Marlowe consumer

Create a group, subscribe it to a queue, and implement one handler.

## The group

`marlowe group create orders-worker --queue orders` creates a group with
at-most-once acknowledgement, which is what a group gets without an explicit
`ack_mode`. A handler that fails therefore loses its message, so anything you
cannot afford to lose is written to a store inside the handler before it
returns.

## The handler

The handler receives one message at a time and returns an outcome. Returning an
error marks the message failed; raising is treated the same way.
