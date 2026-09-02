---
type: Reference
title: "Correlating Quillon logs"
description: "Joining logs across Quillon services for one request, and the fields the join uses."
tags: [quillon, logging, correlation]
status: stable
generated: { by: human:okf-bench, at: 2026-09-11T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-11T09:00:00Z }
stale_after: 2027-11-30
---
# Correlating Quillon logs

Every log line carries the request's trace identifier, and the join across
services is on that field alone.

## The field

Services log the value of `quillon-trace-id` under the `trace` key. A line
without a `trace` key came from a background task rather than a request, and the
background tasks are excluded from the correlation view by default.

## Retention

Correlated views are built on demand over the trailing 14 days of logs; older
requests are reconstructable from the archive but not from the view.
