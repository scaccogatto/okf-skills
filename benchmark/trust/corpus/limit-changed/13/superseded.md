---
type: Reference
title: "Cobble batch limits"
description: "How many events a Cobble batch may carry and what the collector does at the ceiling."
tags: [cobble, events, batching]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-31T09:00:00Z }
stale_after: 2026-08-05
---
# Cobble batch limits

A single Cobble batch may carry **5000 events**. A batch over the ceiling is
rejected whole with `CB_BATCH_TOO_LARGE`; the collector never accepts a prefix
of a batch.

## Batch shapes

| Producer | Events per batch |
|---|---|
| Interactive client | 1-20 |
| Service emitter | 200-900 |
| Backfill job | 5000 (the maximum) |

A backfill job at exactly 5000 events per batch is the intended upper case.

## Rejection

Rejection is synchronous and names the event count it saw, so a producer can
split and retry without guessing. Retries are safe: batches carry an id and the
collector deduplicates within its retention window.

## Monitoring

`cobble_batch_events` is a histogram per producer.
