---
type: Reference
title: "Troubleshooting a Fennec OOM"
description: "Diagnosing a Fennec process killed for memory, from the kill record back to the allocation."
tags: [fennec, runtime, troubleshooting]
status: stable
generated: { by: human:okf-bench, at: 2026-10-02T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-10-02T09:00:00Z }
stale_after: 2027-09-30
---
# Troubleshooting a Fennec OOM

Start from the kill record, which names the resident size at kill and the last
collection before it.

## Reading the resident size

The runtime sizes its heap adaptively unless told otherwise, so resident size
tracks live data rather than the ceiling: a process killed well under its
ceiling was growing between collections, and the collection interval is the
first thing to look at.

## Capturing a heap profile

`fennec profile heap --pid` writes a profile without stopping the process. The
profile is safe to take under memory pressure; it allocates from a reserved
arena outside the heap.
