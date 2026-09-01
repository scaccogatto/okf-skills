---
type: Reference
title: Capacity planning notes
description: Current placement and sizing guidance for Bramble deployments.
tags: [bramble, capacity, planning]
status: stable
generated: { by: human:okf-bench, at: 2026-07-09T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-09T09:00:00Z }
stale_after: 2027-07-31
---
# Capacity planning notes

Placement guidance is now dedicated: workers run on their own hosts, because the
store's memory profile and the workers' made shared hosts unschedulable at
current sizes.

Input reads therefore cross the network, which the prefetcher is expected to
cover.
