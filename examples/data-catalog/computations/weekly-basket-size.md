---
type: Attested Computation
title: Weekly average basket size
description: Mean paid amount per basket for one ISO week, across all stores and online.
tags: [sales, basket, kpi]
status: stable
runtime: bigquery
parameters:
  - { name: week_start, type: date, required: true }
  - { name: store_id, type: string }
executor:
  resource: /references/run-on-bigquery.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: /references/attesters/sql_equality.py
generated: { by: "catalog-agent/1.2", at: "2026-10-15T09:00:00Z" }
sources:
  - id: finance-kpi-sheet
    resource: https://example.com/northwind/finance/kpi-definitions
    title: Finance KPI definitions
    author: "team:finance"
    last_modified: "2026-09-30T00:00:00Z"
---

# Computation

```sql
SELECT AVG(total_amount) AS avg_basket_eur
FROM `northwind-analytics.sales.orders`
WHERE order_date BETWEEN @week_start AND DATE_ADD(@week_start, INTERVAL 6 DAY)
  AND (@store_id IS NULL OR store_id = @store_id)
```

Finance defines basket size on paid amount including VAT, before refunds.[^finance-kpi-sheet]
It reads [Orders](/tables/orders.md). No one has confirmed this query since it
was written, so it carries no `verified` event.

[^finance-kpi-sheet]: Finance KPI definitions
