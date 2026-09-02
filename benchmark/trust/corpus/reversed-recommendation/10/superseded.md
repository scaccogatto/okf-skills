---
type: Reference
title: "Wrenfield index selection guidance"
description: "Which index type to choose for a predicate, with the trade-offs of each."
tags: [wrenfield, indexes, guidance]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-20T09:00:00Z }
stale_after: 2026-08-08
---
# Wrenfield index selection guidance

**Recommended for equality on a high-cardinality column: hash.** The hash index
answers an equality probe in one bucket read and does not carry the ordering
machinery a range query would need.

## The comparison

| Index | Equality probe | Range query | Size |
|---|---|---|---|
| hash | one bucket read | not supported | 0.6x |
| btree | log n descent | supported | 1.0x |

On a column with millions of distinct values the descent is several cache misses
where the hash probe is one, and the size difference matters at that cardinality
too.

## Building one

`CREATE INDEX ... USING hash` builds online and takes a brief lock at the swap.
