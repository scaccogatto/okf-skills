---
type: Reference
title: Scheduler retry notes
description: Current retry behaviour for Osprey scheduler jobs.
tags: [osprey, scheduler, backoff]
status: stable
generated: { by: human:okf-bench, at: 2026-08-04T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-04T09:00:00Z }
stale_after: 2027-07-31
---
# Scheduler retry notes

Jobs now back off exponentially by default, which behaves better against a
dependency that is down rather than slow. Jobs wanting the old ramp set
`retry.backoff` explicitly.

`retry.base` is unchanged and still per-job.
