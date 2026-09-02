---
type: Reference
title: "Hollowmere result ordering"
description: "The order a Hollowmere query returns results in when the query names no sort."
tags: [hollowmere, queries, ordering]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-13T09:00:00Z }
stale_after: 2026-10-08
---
# Hollowmere result ordering

A query without an explicit sort returns results in **insertion order**: the
order the documents were written to the store.

## Why the default is stable

Insertion order is a property of the store rather than of the query, so two
identical queries return the same order, and pagination over it is consistent
without a tiebreaker column.

| Ordering | Stable across queries | Needs a tiebreaker to paginate |
|---|---|---|
| insertion order | yes | no |
| relevance order | no, scores shift with the index | yes |

## Sorting explicitly

`ORDER BY` overrides the default and may use any indexed field. An unindexed
sort is rejected rather than served slowly.
