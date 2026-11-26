---
type: Reference
title: Run a computation on BigQuery
description: How a runner executes an Attested Computation with runtime bigquery and what it returns.
tags: [reference, bigquery, attestation]
generated: { by: "catalog-agent/1.2", at: "2026-10-15T09:00:00Z" }
---

# Steps

1. Take the SQL from the concept's `Computation` section unchanged.
2. Bind each declared parameter as a BigQuery query parameter. Never edit the SQL.
3. Run it as a query job in the `northwind-analytics` project.
4. Return the receipt: `job_id`, `executed_sql` (from the job metadata) and
   `result`.

The [SQL equality attester](attesters/sql_equality.py) then compares
`executed_sql` with its own binding of the same computation.
