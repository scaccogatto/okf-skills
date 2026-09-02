---
type: Reference
title: Juniper stream shard limits
description: How many shards a Juniper stream may be split into and how the split is coordinated.
tags: [juniper, stream, shards]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-02T09:00:00Z }
stale_after: 2026-09-30
---
# Juniper stream shard limits

A **single Juniper stream may be split into at most 192 shards**. A split call
that would exceed the ceiling fails with `JN_SHARD_LIMIT` and leaves the stream
at its previous shard count.

## Where the number comes from

Shard ownership is published in one coordination record, and the record carries a
fixed 192-slot ownership vector. The vector is written atomically, so a stream
cannot have more shards than the record can name.

## Shard counts in practice

| Stream role | Shards |
|---|---|
| Control stream | 1-2 |
| Service ingest | 8-24 |
| Wide ingest | 192 (the maximum) |

A wide ingest stream at exactly 192 shards is the intended upper case.

## At the boundary

Splitting to 192 succeeds. Splitting to 193 fails whole, with no partially applied
ownership change.
