---
type: Decision
title: Event-driven service communication
description: Services publish domain events instead of calling each other's side effects directly.
tags: [adr, architecture, events]
status: stable
generated: { by: human:sam, at: "2026-06-15T16:40:00Z" }
verified: { by: human:dana, at: "2026-06-16T08:15:00Z" }
---

# Context

Early on, [Orders API](/services/orders-api.md) called email, analytics, and
inventory inline at checkout. Each new consumer made checkout slower and more
fragile — one slow dependency failed the whole order.

# Decision

Services own their data and publish **domain events** (`order.paid`,
`order.failed`) to a broker. Consumers subscribe; producers never know who
listens. [Payments API](/services/payments-api.md) stays a synchronous call
because checkout cannot complete without a charge result.

# Consequences

* New consumers attach without touching the checkout path.
* Eventual consistency is now an explicit, documented trade-off.
* Each service needs an idempotent event handler.
