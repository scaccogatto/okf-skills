---
type: Reference
title: "Cobble collector metrics"
description: "Metrics a Cobble collector publishes, including the one counting drops."
tags: [cobble, metrics, collector]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-17T09:00:00Z }
stale_after: 2026-09-08
---
# Cobble collector metrics

Dropped events are counted by **`cobble.drops`**, a counter labelled by stream
and reason.

## Published metrics

| Metric | Type | Labels |
|---|---|---|
| `cobble.drops` | counter | stream, reason |
| `cobble.batch.size` | histogram | stream |
| `cobble.flush.seconds` | histogram | none |

## Reading the drop counter

Reasons are `overflow`, `malformed` and `expired`, and they mean different
things operationally: overflow is capacity, malformed is a producer bug, expired
is a collector that fell behind. Alerting on the unlabelled total mixes all
three and produces an alert nobody can act on.

## Cardinality

Streams are the only unbounded label; a deployment with thousands of streams
should aggregate before shipping.
