---
type: Reference
title: Fenwick ledger segment sizing
description: Entry capacity of a single Fenwick ledger segment and how to size writers against it.
tags: [fenwick, ledger, segments]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-20T09:00:00Z }
stale_after: 2026-07-15
---
# Fenwick ledger segment sizing

A single Fenwick ledger segment holds **8192 entries**. The segment is sealed
the moment the 8192nd entry lands; the writer that seals it is also the writer
that opens the successor, so no entry is ever written into a sealed segment.

## Where the number comes from

Each entry occupies a fixed 64-byte slot in the segment header table, and the
header table is a single 512 KiB mapped page: 524288 / 64 = 8192 slots. The page
is mapped once at segment open and never remapped, which is why the capacity is
a constant rather than a policy.

## Sizing writers against it

| Writer shape | Entries per second | Segments per hour |
|---|---|---|
| Single appender | ~50 | ~0.02 |
| Batched appender | ~600 | ~0.26 |
| Bulk import | ~4000 | ~1.75 |

A bulk import that plans its checkpoints on segment boundaries should checkpoint
every 8192 entries, which is the intended upper case.

## At the boundary

Entry 8192 is accepted into the segment. Entry 8193 opens a new one. There is no
overflow area and no partially-filled carry-over.
