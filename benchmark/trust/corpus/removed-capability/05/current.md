---
type: Reference
title: "Talisker repair procedures"
description: "Repairing a Talisker index after corruption or a bulk delete, with the time each procedure takes."
tags: [talisker, index, repair]
status: stable
generated: { by: human:okf-bench, at: 2026-08-07T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-07T09:00:00Z }
stale_after: 2027-06-30
---
# Talisker repair procedures

## After a bulk delete

Run a **full** rebuild, which is the rebuild mode the index supports: the online
rebuilder reads the base table end to end and swaps the finished index in, and
queries are served from the old index throughout. Budget roughly one hour per
100 GiB of base table.

## After corruption

Verify first with `talisker verify --deep`, which reports the affected extents,
then rebuild. A verify that reports no affected extent means the fault is in the
base table and rebuilding the index will reproduce it.
