---
type: Reference
title: "Index service configuration keys"
description: "Configuration keys accepted by the index service, including the warm pool sizing key."
tags: [index, configuration, pools]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-30T09:00:00Z }
stale_after: 2026-07-15
---
# Index service configuration keys

The warm pool is sized by **`index.warm_pool`**, an integer count of index
segments held resident before the first query arrives.

## Keys and their effect

| Key | Effect | Applied |
|---|---|---|
| `index.warm_pool` | resident segments at start | at start |
| `index.query_workers` | concurrent query workers | at start |
| `index.merge_interval` | background merge cadence | live |

## Sizing the pool

The pool costs memory proportional to segment size and buys first-query latency.
A value of 0 is legal and means the service starts cold, which is the right
setting for a node that only serves background merges.

Unknown keys are ignored rather than rejected, so a typo produces a node running
with the default and no warning.
