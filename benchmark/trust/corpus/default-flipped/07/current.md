---
type: Reference
title: "Osprey incident runbook"
description: "What to do when an Osprey dependency is down and jobs are piling up on retry."
tags: [osprey, scheduler, runbook]
status: stable
generated: { by: human:okf-bench, at: 2026-08-04T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-04T09:00:00Z }
stale_after: 2027-07-31
---
# Osprey incident runbook

When a dependency is down, jobs pile up in retry rather than failing outright.

## What the queue does on its own

Jobs back off exponentially unless `retry.backoff` says otherwise, so the retry
pressure on a downed dependency halves roughly every attempt and the queue does
not need to be paused for the dependency's sake. Pause it only if the retries
themselves are the problem.

## Draining after recovery

`osprey queue release --job` releases held attempts immediately rather than
waiting out the current delay. Release in batches: a full release re-creates the
thundering herd the backoff prevented.
