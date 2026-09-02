---
type: Reference
title: "Orbis session metrics"
description: "Reporting on Orbis session counts and durations, and the queries the reports run."
tags: [orbis, sessions, reporting]
status: stable
generated: { by: human:okf-bench, at: 2026-08-26T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-26T09:00:00Z }
stale_after: 2027-10-31
---
# Orbis session metrics

The nightly report counts live sessions per tenant and their median duration.

## The query

It reads `orbis_session_state` on the reporting replica, grouped by tenant and
bucketed by hour. Running it against the primary is possible and is discouraged:
the table takes a write on every request that touches a session.

## Duration

Duration is close time minus open time, and sessions still open at report time
are excluded rather than truncated, which makes the median stable across runs.
