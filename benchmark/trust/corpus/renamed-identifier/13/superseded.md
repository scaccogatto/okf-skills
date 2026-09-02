---
type: Reference
title: "Wrenfield CLI flags"
description: "Flags the Wrenfield CLI accepts on a query, including plan output."
tags: [wrenfield, cli, queries]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-28T09:00:00Z }
stale_after: 2026-09-18
---
# Wrenfield CLI flags

Pass **`--explain`** to print the query plan instead of executing the query.

## Flags

| Flag | Effect |
|---|---|
| `--explain` | print the plan, execute nothing |
| `--analyze` | execute and print the plan with real row counts |
| `--timeout` | abort after a duration |

## Reading a plan

The plan is printed leaf-first, with the estimated row count beside each node.
An estimate more than an order of magnitude off is the usual cause of a bad join
order, and it means the statistics are stale rather than the planner wrong.

## Statistics

`ANALYZE` refreshes statistics per table and is safe to run against a live
table.
