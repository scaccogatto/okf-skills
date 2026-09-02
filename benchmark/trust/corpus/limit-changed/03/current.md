---
type: Reference
title: "Corvid mesh capacity planning"
description: "Planning node and channel counts for a Corvid mesh from a subscriber population."
tags: [corvid, mesh, capacity]
status: stable
generated: { by: human:okf-bench, at: 2026-08-24T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-24T09:00:00Z }
stale_after: 2027-09-30
---
# Corvid mesh capacity planning

Plan a mesh from its subscriber population rather than from its publisher count:
subscribers are what the delivery path is dimensioned for.

## Channels from subscribers

A channel carries at most 108 concurrent subscriptions, so a population of a
thousand subscribers needs at least ten channels, and in practice twelve to
leave headroom for a rolling restart.

## Node sizing

Each node holds delivery cursors for the channels it hosts, at roughly 12 KiB
per cursor. Nodes are sized to hold a whole channel rather than a fraction of
one, so channel placement is per node and never split.
