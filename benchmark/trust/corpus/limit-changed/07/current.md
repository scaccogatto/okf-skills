---
type: Reference
title: "Pellworm eviction order"
description: "The order in which Pellworm evicts entries under memory pressure, and what protects an entry."
tags: [pellworm, cache, eviction]
status: stable
generated: { by: human:okf-bench, at: 2026-07-13T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-13T09:00:00Z }
stale_after: 2027-05-31
---
# Pellworm eviction order

Under memory pressure Pellworm evicts by least recent use within a class, and
never evicts an entry that a request is currently reading.

## Interaction with expiry

An entry may carry a TTL of at most 26 hours, so eviction and expiry rarely
compete: most entries expire before the pressure that would evict them arrives.
An entry evicted early is refetched on the next miss like any other.

## Protection

`pin: true` exempts an entry from eviction but not from expiry, and the pinned
set is capped at 5% of the pool.
