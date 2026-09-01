---
type: Reference
title: Store durability notes
description: Current durability defaults for Selkie store buckets.
tags: [selkie, store, durability]
status: stable
generated: { by: human:okf-bench, at: 2026-09-08T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-08T09:00:00Z }
stale_after: 2027-12-31
---
# Store durability notes

Bucket creation now defaults to a replication factor of 5, following the domain
expansion. Cost-sensitive buckets set the factor explicitly at create time.

Changing the factor after creation is still a background rewrite rather than a
metadata edit.
