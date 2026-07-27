---
type: Service
title: Payments API
description: Captures charges and refunds via the upstream payment processor.
resource: https://github.com/acme/storefront/tree/main/services/payments
tags: [payments, money, platform]
status: stable
generated: { by: doc_agent/1.0, at: "2026-06-16T11:05:00Z" }
sources:
  - id: payments-readme
    resource: https://github.com/acme/storefront/tree/main/services/payments
    title: Payments service README
    author: team:payments
    last_modified: 2026-06-16
---

# Overview

Wraps the third-party payment processor behind a stable internal contract. Called
synchronously by the [Orders API](/services/orders-api.md) during checkout, it
authenticates the caller through the [Auth API](/services/auth-api.md) and records
every charge attempt in the [Orders database](/datasets/orders-db.md). Like the
rest of the platform it follows the
[event-driven decision](/decisions/event-driven.md) for downstream notification.

# Endpoints

| Method | Path                | Description                               |
|--------|---------------------|-------------------------------------------|
| `POST` | `/charges`          | Capture a charge for an order.            |
| `POST` | `/charges/{id}/void`| Void or refund a prior charge.            |
| `POST` | `/webhooks/processor`| Ingest processor status callbacks.       |

# Idempotency

Every `POST /charges` requires an `Idempotency-Key` header (the order id). Retries
with the same key return the original result rather than double-charging — the
single most important invariant in the service.[^payments-readme]

[^payments-readme]: Payments service README

# Operations

When charge success rate drops, follow the
[Payment failures runbook](/runbooks/payment-failures.md).
