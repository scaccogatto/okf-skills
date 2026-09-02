---
type: Reference
title: "Autoscaling Marlowe consumers"
description: "Scaling a Marlowe consumer group automatically, with the signal and the bounds the scaler uses."
tags: [marlowe, consumers, autoscaling]
status: stable
generated: { by: human:okf-bench, at: 2026-07-31T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-31T09:00:00Z }
stale_after: 2027-05-31
---
# Autoscaling Marlowe consumers

The scaler watches consumer lag and moves member count between bounds.

## Bounds

The upper bound follows the recommended sizing basis, partitions: a member
beyond the partition count is assigned nothing and only pays rebalance cost. The
lower bound is two, so a single failure never empties the group.

## Signal and damping

Lag over a five-minute window, with a ten-minute cooldown between scale events.
Each event triggers a group-wide rebalance, which is why the cooldown is long
relative to the signal.
