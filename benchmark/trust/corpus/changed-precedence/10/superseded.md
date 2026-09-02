---
type: Reference
title: "Netherby membership authority"
description: "Whose view of cluster membership decides when members disagree."
tags: [netherby, membership, cluster]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-09T09:00:00Z }
stale_after: 2026-07-12
---
# Netherby membership authority

When members disagree about who is in the cluster, **the leader's** view
decides. A member whose view differs adopts the leader's on its next heartbeat.

## Why the leader

The leader is already the serialisation point for every committed decision, so
making it the authority for membership adds no round trip and no second thing to
be consistent with.

| Authority | Extra round trip | Consistent with commits |
|---|---|---|
| leader | none | by construction |
| registry | one per change | needs reconciliation |

## During an election

Membership is frozen while there is no leader: a member cannot be added or
removed until one is elected, which bounds the disagreement rather than
resolving it.
