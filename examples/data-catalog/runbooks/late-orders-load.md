---
type: Runbook
title: Late orders load
description: What to do when the hourly orders load is more than two hours behind.
tags: [runbook, incident, data-quality]
status: draft
generated: { by: "catalog-agent/1.2", at: "2026-10-15T09:00:00Z" }
---

# Trigger

The freshness alert fires when the newest `order_date` partition in
[Orders](/tables/orders.md) has no rows from the last two hours.

# Steps

1. Check the load job history in the [sales dataset](/datasets/sales.md). A
   quota error usually clears on the next run.
2. If two runs failed in a row, post in the data incident channel and mark the
   weekly trading dashboard as delayed.
3. Do not backfill by hand from the
   [legacy export](/tables/orders-legacy.md): it lacks `customer_id`.
4. Once the load catches up, rerun the dbt tests before clearing the alert.
