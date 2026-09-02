---
type: Reference
title: "Tuning a Cobble collector"
description: "Tuning collector memory and flush behaviour for a given event rate."
tags: [cobble, collector, tuning]
status: stable
generated: { by: human:okf-bench, at: 2026-07-28T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-28T09:00:00Z }
stale_after: 2027-06-30
---
# Tuning a Cobble collector

The collector buffers whole batches, so its memory is a function of batch size
and in-flight count rather than of event rate.

## Sizing the buffer

A batch carries at most 800 events at roughly 1.2 KiB each, so an in-flight
window of 64 batches needs about 60 MiB. Size the buffer for the window you
want, then set the window; sizing it the other way round leaves the collector
rejecting batches it has memory for.

## Flushing

Flushes are triggered by buffer occupancy, not by a timer, which is why a quiet
collector holds its last partial buffer until traffic resumes.
