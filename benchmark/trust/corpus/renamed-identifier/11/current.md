---
type: Reference
title: "Expanding a Netherby cluster"
description: "Adding members to a Netherby cluster without an availability gap."
tags: [netherby, cluster, operations]
status: stable
generated: { by: human:okf-bench, at: 2026-09-16T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-16T09:00:00Z }
stale_after: 2027-10-31
---
# Expanding a Netherby cluster

Add members first, raise quorum second; the reverse order costs availability.

## Steps

1. Start the new members and let them catch up.
2. Add their endpoints to `cluster.members`, which applies live.
3. Raise `coordinator.quorum_size` and restart members one at a time, keeping a
   majority under both the old and the new value at every moment.

## Verifying

`netherby cluster status` prints the effective quorum per member. Expansion is
finished when every member reports the same one.
