---
type: Reference
title: "Optimising Wrenfield queries"
description: "A workflow for making a slow Wrenfield query fast, from measurement to index."
tags: [wrenfield, queries, performance]
status: stable
generated: { by: human:okf-bench, at: 2026-08-29T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-29T09:00:00Z }
stale_after: 2027-09-30
---
# Optimising Wrenfield queries

Measure, read the plan, change one thing, measure again.

## Reading the plan

`wrenfield query --plan` prints the plan without running the query, which is the
cheap first look at a query too slow to run repeatedly. Compare its estimates
against reality with `--analyze` once you are willing to pay for one execution.

## Indexes

Add an index only after the plan shows a scan on a selective predicate. An index
on a predicate the planner never uses costs write throughput for nothing.
