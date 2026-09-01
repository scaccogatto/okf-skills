---
type: Reference
title: Vireo metric catalogue
description: Metrics published by Vireo, including the one reporting ingest lag.
tags: [vireo, metrics, catalogue]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-06T09:00:00Z }
stale_after: 2026-09-01
---
# Vireo metric catalogue

Ingest lag is published as **`vireo.queue.lag`**, a gauge in seconds sampled
every 10 seconds at the ingest head.

## Published metrics

| Metric | Type | Unit |
|---|---|---|
| `vireo.queue.lag` | gauge | seconds |
| `vireo.queue.depth` | gauge | messages |
| `vireo.batch.flushes` | counter | flushes |

## Reading the lag metric

`vireo.queue.lag` is the age of the oldest unacknowledged record, not a moving
average, so it steps rather than drifts. Alerting on it should use a duration
condition rather than a single sample: a one-sample spike is a flush boundary,
not an incident.

Dashboards built before the sampler rewrite may still chart it as a counter
delta, which reads roughly right and is wrong at restarts.
