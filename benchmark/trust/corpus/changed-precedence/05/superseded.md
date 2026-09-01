---
type: Reference
title: Bramble dispatch order
description: How Bramble picks between two eligible tasks in the same worker lane.
tags: [bramble, dispatch, scheduling]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-01T09:00:00Z }
stale_after: 2026-09-01
---
# Bramble dispatch order

When two tasks in the same lane are eligible, the scheduler dispatches **the
higher priority** first. Submission time is consulted only to break a tie between
equal priorities.

## Dispatch rules

| Rank | Criterion |
|---|---|
| 1 | priority, descending |
| 2 | submission time, ascending |
| 3 | task id, ascending |

## Why priority ranks first

Lanes are shared between interactive and background work, and priority is the
only signal that distinguishes them once both are queued. Ranking priority first
is what keeps an interactive task from queueing behind an hour of backfill that
was submitted a second earlier.

The cost is starvation: a steady stream of high-priority work can hold a
low-priority task indefinitely, and the scheduler does not age priorities.
