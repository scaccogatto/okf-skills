---
type: BigQuery Dataset
title: Sales dataset
description: BigQuery dataset holding Northwind Grocers store and online sales.
resource: northwind-analytics.sales
tags: [sales, bigquery, warehouse]
status: stable
generated: { by: "catalog-agent/1.2", at: "2026-10-15T09:00:00Z" }
verified: { by: "human:priya.shah", at: "2026-11-02T14:30:00Z" }
sources:
  - id: warehouse-console
    resource: https://console.cloud.google.com/bigquery?project=northwind-analytics
    title: BigQuery console, northwind-analytics project
    author: "team:data-platform"
    last_modified: "2026-10-14T00:00:00Z"
---

# Overview

The `sales` dataset holds every completed sale from the 42 stores and the
online shop, in the EU multi-region.[^warehouse-console] The data platform team
owns it. Analysts read it, only the load jobs write it.

# Tables

| Table | What it holds |
|-------|---------------|
| [orders](/tables/orders.md) | One row per completed order, loaded hourly. |
| [orders_daily_export](/tables/orders-legacy.md) | Deprecated daily export, kept until its retention ends. |

Retention follows the [sales data retention policy](/policies/data-retention.md).

[^warehouse-console]: BigQuery console, northwind-analytics project
