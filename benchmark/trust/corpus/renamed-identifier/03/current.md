---
type: Reference
title: "Index node bootstrap"
description: "What an index node does between process start and serving its first query."
tags: [index, bootstrap, startup]
status: stable
generated: { by: human:okf-bench, at: 2026-06-24T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-24T09:00:00Z }
stale_after: 2027-06-30
---
# Index node bootstrap

A node opens its segment set, fills its pools and only then joins the query
ring.

## Filling the pools

`index.prefetch_pool` sets how many segments are resident before the node joins;
the node reads them in segment order and reports progress on the admin socket.
A node with the pool set to zero joins immediately and serves its first queries
from disk.

## Joining the ring

Joining is a single write to the ring record. A node that fails to join retries
with jitter and keeps its pools warm meanwhile.
