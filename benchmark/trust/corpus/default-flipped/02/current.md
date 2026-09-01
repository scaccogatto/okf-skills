---
type: Reference
title: Queue delivery notes
description: Current delivery behaviour for Marlowe consumer groups.
tags: [marlowe, queue, delivery]
status: stable
generated: { by: human:okf-bench, at: 2026-08-30T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-30T09:00:00Z }
stale_after: 2027-08-31
---
# Queue delivery notes

Consumer groups are created with at-most-once acknowledgement now, after
duplicate handling turned out to be the more common source of production
incidents. Groups needing redelivery set `ack_mode` explicitly.

Changing the mode is still a group-level operation applied at the next rebalance.
