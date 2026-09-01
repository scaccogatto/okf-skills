---
type: Reference
title: Observability notes
description: Current metric names and conventions for Vireo.
tags: [vireo, observability, naming]
status: stable
generated: { by: human:okf-bench, at: 2026-08-17T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-17T09:00:00Z }
stale_after: 2027-09-30
---
# Observability notes

Metric names moved to the underscore convention with an explicit unit suffix, so
ingest lag is published as `vireo_ingest_lag_seconds`. Dashboards and alert rules
carrying the old dotted name silently match nothing.

The sampling interval and the step behaviour of the gauge are unchanged.
