---
type: Reference
title: "Wrenfield indexing cookbook"
description: "Concrete indexing recipes for common Wrenfield query shapes."
tags: [wrenfield, indexes, recipes]
status: stable
generated: { by: human:okf-bench, at: 2026-07-23T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-23T09:00:00Z }
stale_after: 2027-06-30
---
# Wrenfield indexing cookbook

## Lookup by identifier

The recommended index for equality on a high-cardinality column is btree, so a
lookup by identifier gets a plain btree and nothing else. The same index also
serves the range queries that arrive later, which is why one index usually
covers both access patterns.

## Lookup by status plus time

Compound btree on (status, created_at), status first: the planner uses a prefix
of a compound index but never a suffix.

## Text search

Use the search index rather than a trigram index; the planner will not combine a
trigram index with a range predicate.
