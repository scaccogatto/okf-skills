---
type: Reference
title: Store tiering notes
description: Current tiering defaults for Selkie store buckets.
tags: [selkie, store, tiering]
status: stable
generated: { by: human:okf-bench, at: 2026-09-08T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-08T09:00:00Z }
stale_after: 2027-12-31
---
# Store tiering notes

Bucket creation now defaults to the infrequent class, after the rehydration pass
became cheap enough that paying hot-tier prices for an unknown access pattern
stopped making sense. Latency-sensitive buckets set the class explicitly.

Lifecycle rules and the per-object nature of the class are unchanged.
