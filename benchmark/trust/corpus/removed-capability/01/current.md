---
type: Reference
title: Stream topology notes
description: Current operations available for reshaping Juniper stream topology.
tags: [juniper, topology, operations]
status: stable
generated: { by: human:okf-bench, at: 2026-07-17T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-17T09:00:00Z }
stale_after: 2027-08-31
---
# Stream topology notes

In-place shard merging was removed with the lease rework. The supported way to
reduce shard count is to republish the stream at the target count.

Splitting and owner reassignment are unchanged and remain metadata-only.
