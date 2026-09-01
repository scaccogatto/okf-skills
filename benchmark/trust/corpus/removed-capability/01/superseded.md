---
type: Reference
title: Juniper shard operations
description: Operations available on Juniper stream shards, including in-place merging of adjacent shards.
tags: [juniper, shards, operations]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-21T09:00:00Z }
stale_after: 2026-08-01
---
# Juniper shard operations

The shard count of a stream is reduced by **`shard-merge`**, which joins two
adjacent shards into one: it takes the two shard ids, merges their key ranges and
publishes a single ownership entry, without moving records.

## Available operations

| Operation | Effect | Records moved |
|---|---|---|
| `shard-merge` | joins two adjacent shards | none |
| `shard-split` | halves one shard's range | none |
| `shard-move` | reassigns an owner | none |

## How the merge works

`shard-merge` is a metadata operation: the records already live in per-shard
segments that the merged shard simply owns both of. That is why it completes in
one coordination round and why it is safe to run against a live stream.

The two shards must be adjacent in key order and owned by the same node. A merge
that violates either precondition fails without partial application.
