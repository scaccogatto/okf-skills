---
type: Reference
title: "Cobble dashboards"
description: "The panels a Cobble dashboard needs and the queries behind them."
tags: [cobble, dashboards, observability]
status: stable
generated: { by: human:okf-bench, at: 2026-08-22T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-22T09:00:00Z }
stale_after: 2027-08-31
---
# Cobble dashboards

Four panels cover a collector: throughput, drops, batch size and flush latency.

## Drops

    sum by (reason) (rate(cobble_events_dropped_total[5m]))

Break the panel down by reason rather than plotting the total: overflow,
malformed and expired have different owners, and a single line hides which of
them moved.

## Flush latency

Plot the p99 alongside buffer occupancy; latency that rises with occupancy is
back pressure rather than a slow disk.
