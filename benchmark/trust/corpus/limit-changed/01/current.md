---
type: Reference
title: Halyard relay backpressure
description: How a Halyard relay applies backpressure to producers, and the frame budget the mechanism assumes.
tags: [halyard, relay, backpressure]
status: stable
generated: { by: human:okf-bench, at: 2026-07-30T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-30T09:00:00Z }
stale_after: 2027-06-30
---

# Halyard relay backpressure

A relay signals backpressure through the credit field of its acknowledgement,
which tells the producer how many further frames it may put in flight. A
producer that ignores the credit is disconnected rather than throttled.

## Credit arithmetic

Credit is granted in whole frames, and a frame carries at most 112 KiB of
payload, so a producer holding four credits may have 448 KiB outstanding. Credit
is replenished on acknowledgement, not on a timer.

## Refusals

An oversize frame is refused whole, with `HL_FRAME_OVERSIZE`, and refusal does
not consume credit.
