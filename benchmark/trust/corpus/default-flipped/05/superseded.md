---
type: Reference
title: Fennec runtime heap sizing
description: Heap sizing mode used by the Fennec runtime by default and how the heap is reserved.
tags: [fennec, runtime, heap]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-05T09:00:00Z }
stale_after: 2026-11-01
---
# Fennec runtime heap sizing

The Fennec runtime uses **static heap sizing by default**. The heap is reserved
at process start from the configured ceiling and never returned to the operating
system while the process lives.

## Why static was the default

A statically sized heap makes the process footprint a constant, which is what
made co-tenancy planning arithmetic rather than guesswork: the scheduler can bin
processes by their ceiling and never see a surprise.

| Mode | Footprint | Reclaim |
|---|---|---|
| static | constant at ceiling | never |
| adaptive | grows and shrinks | at collection |

## Selecting the mode

`heap.mode` accepts `static` or `adaptive`. The mode is read once at start; there
is no way to switch a live process between them.
