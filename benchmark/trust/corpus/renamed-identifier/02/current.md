---
type: Reference
title: "Vireo alerting cookbook"
description: "Alert rules for Vireo ingest, with the conditions and durations each rule uses."
tags: [vireo, alerting, rules]
status: stable
generated: { by: human:okf-bench, at: 2026-08-17T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-17T09:00:00Z }
stale_after: 2027-09-30
---
# Vireo alerting cookbook

Three rules cover the ingest path: lag, depth and flush failure.

## Lag

    alert: IngestLagHigh
    expr: vireo_ingest_lag_seconds > 300
    for: 10m

The duration matters more than the threshold: the gauge steps at flush
boundaries, and a rule without `for` fires on every boundary.

## Depth and flushes

Depth alerts on absolute backlog and pairs with the lag rule; a depth alert
without a lag alert usually means a stuck consumer rather than slow ingest.
