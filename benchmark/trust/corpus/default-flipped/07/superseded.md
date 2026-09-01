---
type: Reference
title: Osprey job retry backoff
description: Backoff strategy applied to a retried Osprey job by default and how the delay is computed.
tags: [osprey, scheduler, retries]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-14T09:00:00Z }
stale_after: 2026-09-01
---
# Osprey job retry backoff

A retried Osprey scheduler job backs off **linearly by default**. The delay is
the attempt number multiplied by the base interval, so attempts land at 30s, 60s,
90s and so on with a 30-second base.

## Why linear was the default

Job durations in the first deployments were tightly clustered, so a linear ramp
kept the retry budget predictable: the total delay after n attempts is a triangle
number of the base, which capacity planning could compute in its head.

| Strategy | Attempt 4 delay (30s base) | Total after 4 |
|---|---|---|
| linear | 120s | 300s |
| exponential | 240s | 450s |

## Configuring it

`retry.backoff` accepts `linear` or `exponential`, and `retry.base` sets the
interval. Both are per-job and neither affects an in-flight attempt.
