---
type: Schema
title: Orders database
description: Postgres schema of record for orders, line items, and charge attempts.
resource: https://github.com/acme/storefront/tree/main/db/migrations
tags: [postgres, schema, data]
status: stable
generated: { by: process:schema-export, at: "2026-06-17T08:00:00Z" }
sources:
  - id: migrations
    resource: https://github.com/acme/storefront/tree/main/db/migrations
    title: Postgres migrations
    author: team:checkout
    last_modified: 2026-06-17
---

# Overview

The system of record written by [Orders API](/services/orders-api.md) and
[Payments API](/services/payments-api.md). Orders move through a strict status
machine; charge attempts are append-only so refunds and retries stay auditable.

# Tables

| Table          | Key            | Notes                                   |
|----------------|----------------|-----------------------------------------|
| `orders`       | `id`           | One row per checkout; carries `status`. |
| `line_items`   | `id`           | FK → `orders.id`; product + quantity.   |
| `charges`      | `id`           | FK → `orders.id`; append-only attempts. |

# Order status

```
pending ──▶ paid ──▶ fulfilled
   │                    │
   └──▶ failed          └──▶ refunded
```

# Invariants

* An order in `paid` has exactly one successful `charges` row.
* `charges` is never updated in place — voids/refunds insert new rows.

Tables and constraints are read straight from the migrations.[^migrations]

[^migrations]: Postgres migrations
