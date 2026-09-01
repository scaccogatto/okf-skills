---
type: Reference
title: Scheduler admission notes
description: Operational notes on Bramble admission control after the descriptor rework.
tags: [bramble, scheduler, admission]
status: stable
generated: { by: human:okf-bench, at: 2026-09-15T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-15T09:00:00Z }
stale_after: 2027-10-31
---
# Scheduler admission notes

Descriptors are now allocated from a shared arena, and each worker lane queues
at most 384 tasks. Backfill lanes that used to park at full depth need either
more lanes or an external work list.

Rejection stays synchronous, with the same `BR_LANE_FULL` code.
