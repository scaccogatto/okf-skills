---
type: BigQuery Table
title: Orders
description: One row per completed order, in stores and online, loaded hourly.
resource: northwind-analytics.sales.orders
tags: [sales, orders, bigquery]
status: stable
generated: { by: "catalog-agent/1.2", at: "2026-11-20T08:00:00Z" }
verified: { by: "process:dbt-tests", at: "2026-11-25T03:00:00Z" }
stale_after: "2027-05-20"
sources:
  - id: dbt-model
    resource: https://example.com/northwind/dbt/models/sales/orders.sql
    title: dbt model sales.orders
    author: "team:data-platform"
    last_modified: "2026-11-19T16:00:00Z"
---

# Overview

Each row is one [basket](/glossary/basket.md) that reached payment. The table is
partitioned by `order_date` and clustered by `store_id`.[^dbt-model] It lives in
the [sales dataset](/datasets/sales.md) and replaces the
[legacy daily export](/tables/orders-legacy.md).

The nightly dbt tests check uniqueness of `order_id` and that `total_amount` is
never negative. Their last passing run is recorded as a `process:` verification.

# Schema

| Column | Type | Description |
|--------|------|-------------|
| `order_id` | STRING | Unique order id. |
| `order_date` | DATE | Local store date of payment. Partition column. |
| `store_id` | STRING | Store code, `online` for the web shop. |
| `customer_id` | STRING | Loyalty id, null for anonymous buyers. |
| `item_count` | INT64 | Number of line items. |
| `total_amount` | NUMERIC | Paid amount in EUR, after discounts, including VAT. |

[^dbt-model]: dbt model sales.orders
