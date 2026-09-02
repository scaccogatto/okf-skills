---
type: Reference
title: "Pellworm cache warming guidance"
description: "Recommended warming strategy for a Pellworm cache after a deployment."
tags: [pellworm, cache, warming]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-14T09:00:00Z }
stale_after: 2026-10-15
---
# Pellworm cache warming guidance

**Recommended strategy: eager.** A deployment should warm the cache from the
known working set before the instance takes traffic.

## The comparison

| Strategy | First-minute latency | Origin load at deploy |
|---|---|---|
| eager | steady state | one warm pass |
| lazy | origin latency | one miss per key per instance |

An instance that takes traffic cold serves its first minutes at origin latency,
and in a rolling deploy that window repeats per instance. Eager warming moves
the cost into a phase where nothing is waiting on it.

## Running the warm pass

The warm pass reads the previous instance's key census and fetches in key order,
which keeps the origin's own cache effective while it serves the pass.
