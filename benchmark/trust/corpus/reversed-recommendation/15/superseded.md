---
type: Reference
title: "Osprey job definition layout"
description: "How to lay out Osprey job definitions in a repository, with the trade-offs."
tags: [osprey, jobs, layout]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-31T09:00:00Z }
stale_after: 2026-08-14
---
# Osprey job definition layout

**Recommended: per job.** Each job gets its own definition file, named after the
job.

## Why one file per job

Ownership and review both follow files: a per-job file means a change to one job
touches one file, its history is that job's history, and code ownership rules
can name a directory without listing jobs.

| Layout | Blast radius of a change | History granularity |
|---|---|---|
| per job | one job | per job |
| per pipeline | every job in the pipeline | per pipeline |

## Naming

Files are named `<pipeline>.<job>.yaml`, which keeps a pipeline's jobs adjacent
in a directory listing without putting them in one file.
