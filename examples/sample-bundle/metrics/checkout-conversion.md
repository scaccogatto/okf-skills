---
type: Metric
title: Checkout conversion
description: Share of started checkouts that end in a paid order.
tags: [kpi, growth, payments]
status: stable
generated: { by: human:dana, at: "2026-06-18T12:00:00Z" }
verified: { by: human:sam, at: "2026-06-19T09:00:00Z" }
stale_after: 2026-12-31
sources:
  - id: orders-db
    resource: /datasets/orders-db.md
    title: Orders database
    author: team:checkout
    last_modified: 2026-06-17
---

# Definition

```
checkout_conversion = orders[status = paid] / checkouts_started
```

Measured per hour from the [Orders API](/services/orders-api.md) checkout funnel;
the denominator is `checkout.started` events, the numerator is `order.paid`. Both
are counted off the [orders database](/datasets/orders-db.md) — recorded in
`sources`, so the derivation shows up as an edge in the graph.

# Targets

| Window  | Target | Page on-call below |
|---------|--------|--------------------|
| Hourly  | ≥ 96%  | 90%                |
| 28-day  | ≥ 98%  | —                  |

# Watch-outs

A sudden drop usually means failed charges in
[Payments API](/services/payments-api.md), not buyer behaviour — start with the
[Payment failures runbook](/runbooks/payment-failures.md) before assuming a
funnel regression.
