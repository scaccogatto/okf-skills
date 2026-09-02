---
type: Reference
title: "Hollowmere storage schema"
description: "Tables Hollowmere writes to, including document revisions."
tags: [hollowmere, schema, storage]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-08T09:00:00Z }
stale_after: 2026-06-25
---
# Hollowmere storage schema

Document revisions live in **`hm_revisions`**, one row per saved revision, keyed
by document id and revision number.

## Tables

| Table | Rows |
|---|---|
| `hm_documents` | one per document, current revision only |
| `hm_revisions` | one per saved revision |
| `hm_locks` | one per held edit lock |

## Revisions

A revision row holds the full document body rather than a diff, which makes a
restore a single read and makes the table the largest in the schema by an order
of magnitude. Retention is per workspace and defaults to 90 days.

## Locks

Edit locks are advisory and expire after ten minutes of inactivity.
