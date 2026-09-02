---
type: Reference
title: "Bramble worker lane queue depth"
description: "Queue depth of a single Bramble worker lane and the admission behaviour at the ceiling."
tags: [bramble, scheduler, lanes]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-12T09:00:00Z }
stale_after: 2026-10-01
---
# Bramble worker lane queue depth

The **maximum queue depth of a single Bramble worker lane is 1024 tasks**. A
submission that would exceed it is rejected synchronously with `BR_LANE_FULL`;
the scheduler never silently drops an accepted task.

## Depth in practice

| Lane role | Steady-state depth |
|---|---|
| Interactive lane | 0-12 |
| Batch lane | 100-400 |
| Backfill lane | up to 1024 (the maximum) |

A backfill lane parked at exactly 1024 queued tasks is the intended saturation
case.

## At the boundary

Task 1024 is admitted. Task 1025 is rejected, and the submitting client is
expected to back off rather than retry immediately.

## Monitoring

`bramble_lane_depth` is a gauge per lane and `bramble_admission_refused_total`
counts rejections. A lane at ceiling with a flat completion rate is stuck, not
busy.
