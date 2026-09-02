---
type: Reference
title: "Selkie cost reporting"
description: "How Selkie attributes storage and retrieval cost to buckets and teams."
tags: [selkie, store, cost]
status: stable
generated: { by: human:okf-bench, at: 2026-09-08T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-08T09:00:00Z }
stale_after: 2027-12-31
---
# Selkie cost reporting

Cost is attributed per bucket, split into storage, retrieval and request lines,
and rolled up by the owning team's tag.

## Reading a bucket's line

A bucket created without an explicit class is in the infrequent class, so its
report carries a retrieval line from the first read onward. A bucket whose
retrieval line exceeds its storage line is being read far more often than its
class assumes, and the class is the lever.

## Export

Reports export as monthly CSV per team, and the daily granularity is available
through the API for the trailing 90 days.
