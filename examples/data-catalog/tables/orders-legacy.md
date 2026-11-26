---
type: BigQuery Table
title: Orders (legacy)
description: The old daily orders export, replaced by the hourly orders table.
resource: northwind-analytics.sales.orders_daily_export
tags: [sales, orders, bigquery, legacy]
status: deprecated
superseded_by: /tables/orders.md
generated: { by: "catalog-agent/1.2", at: "2026-11-20T08:00:00Z" }
---

# Overview

A daily CSV import that ran until 2026-11-19. It has the same columns as
[Orders](/tables/orders.md) except `customer_id`. Do not build new reports on
it. It is kept read-only until the
[retention policy](/policies/data-retention.md) lets it be dropped.
