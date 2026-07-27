---
type: Service
title: Orders API
description: Owns the order lifecycle — cart checkout, fulfilment, and refunds.
resource: https://github.com/acme/storefront/tree/main/services/orders
tags: [orders, checkout, platform]
status: stable
generated: { by: doc_agent/1.0, at: "2026-06-16T09:20:00Z" }
verified:
  - { by: human:dana, at: "2026-06-20T09:00:00Z" }
  - { by: process:contract-tests, at: "2026-06-26T02:00:00Z" }
sources:
  - id: orders-readme
    resource: https://github.com/acme/storefront/tree/main/services/orders
    title: Orders service README
    author: team:checkout
    last_modified: 2026-06-15
---

# Overview

The heart of the storefront. Authenticates callers through the
[Auth API](/services/auth-api.md), charges them through the
[Payments API](/services/payments-api.md), and persists state to the
[Orders database](/datasets/orders-db.md). It emits domain events rather than
calling downstream consumers directly — see the
[event-driven decision](/decisions/event-driven.md).

# Endpoints

| Method | Path                 | Description                                |
|--------|----------------------|--------------------------------------------|
| `POST` | `/orders`            | Create an order from a cart and charge it. |
| `GET`  | `/orders/{id}`       | Fetch an order and its line items.         |
| `POST` | `/orders/{id}/refund`| Refund an order (full or partial).         |

# Checkout flow

1. Verify the caller's token (`scope: orders:write`).
2. Reserve stock and write a `pending` order to the
   [Orders database](/datasets/orders-db.md).
3. Call [Payments API](/services/payments-api.md) `POST /charges`.
4. On success, mark the order `paid` and publish `order.paid`.

This conversion funnel is tracked by the
[Checkout conversion metric](/metrics/checkout-conversion.md).

# Events

| Event         | When                          |
|---------------|-------------------------------|
| `order.paid`  | Payment captured successfully |
| `order.failed`| Charge declined or timed out  |

Endpoints and events are transcribed from the service README.[^orders-readme]

[^orders-readme]: Orders service README
