---
type: Reference
title: "Wrenfield table limits"
description: "Structural limits of a Wrenfield table, including its column count."
tags: [wrenfield, tables, limits]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-26T09:00:00Z }
stale_after: 2026-09-10
---
# Wrenfield table limits

A Wrenfield table may have **at most 1024 columns**. A DDL statement asking for
more fails with `WF_TOO_MANY_COLUMNS` and the table is not created.

## Structural limits

| Structure | Limit |
|---|---|
| Columns per table | 1024 |
| Indexes per table | 32 |
| Partitions per table | 4096 |

## Wide tables in practice

Tables above a few hundred columns are usually a struct that wants normalising,
but the ceiling exists for generated schemas, where 1024 columns is the intended
upper case.

## Altering a table

Adding a column is metadata-only; dropping one rewrites the table. A table at
the ceiling cannot gain a column even if others are dropped in the same
statement, because the check runs before the drop.
