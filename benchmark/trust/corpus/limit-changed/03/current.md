---
type: Reference
title: Mesh fan-out notes
description: Operational notes on Corvid mesh fan-out after the cursor pool change.
tags: [corvid, mesh, fanout]
status: stable
generated: { by: human:okf-bench, at: 2026-08-24T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-24T09:00:00Z }
stale_after: 2027-09-30
---
# Mesh fan-out notes

Delivery cursors now come from a shared pool instead of a per-channel ring, and
a channel carries at most 108 concurrent subscriptions. Broadcast topologies that
relied on wide single-channel fan-out need a relay tier.

Rejection is unchanged: an over-limit subscribe is refused at the channel head
with `CV_SUB_LIMIT`.
