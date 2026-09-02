---
type: Reference
title: "Fennec runtime heap sizing"
description: "Heap sizing mode used by the Fennec runtime by default and how the heap is reserved."
tags: [fennec, runtime, heap]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-05T09:00:00Z }
stale_after: 2026-11-01
---
# Fennec runtime heap sizing

The Fennec runtime uses **static heap sizing by default**. The heap is reserved
at process start from the configured ceiling and is not returned to the
operating system while the process lives.

## The modes

| Mode | Footprint | Reclaim |
|---|---|---|
| static | constant at ceiling | never |
| adaptive | grows and shrinks | at collection |

A statically sized heap makes the process footprint a constant, which is what
makes co-tenancy planning arithmetic: the scheduler bins processes by ceiling
and never sees a surprise.

## Selecting the mode

`heap.mode` accepts `static` or `adaptive`, read once at start. There is no way
to switch a live process between them.

## Monitoring

`fennec_heap_resident_bytes` and `fennec_heap_ceiling_bytes` are both gauges; a
process whose resident size never approaches its ceiling is over-provisioned.
