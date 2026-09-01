---
type: Reference
title: Runtime memory notes
description: Current memory behaviour of the Fennec runtime.
tags: [fennec, runtime, memory]
status: stable
generated: { by: human:okf-bench, at: 2026-10-02T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-10-02T09:00:00Z }
stale_after: 2027-09-30
---
# Runtime memory notes

Processes now start in adaptive heap mode, returning pages at collection time.
Placement planning that assumed a constant footprint should pin `heap.mode`
instead.

The mode is still read once at start and cannot be switched on a live process.
