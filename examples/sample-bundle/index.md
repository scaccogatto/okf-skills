---
okf_version: "0.2"
---

# Storefront — Sample OKF Bundle

A small, conformant bundle that documents a fictional online store backend. It
shows the knowledge sources OKF targets — **code** (services, schema),
**curated decisions** (ADRs), and **operations** (runbooks, metrics) — and how
markdown links turn a folder of files into a navigable knowledge graph.

> Render it yourself: `uv run skills/visualize/scripts/okf_visualize.py examples/sample-bundle`

# Services

* [Auth API](services/auth-api.md) — issues and verifies JWTs.
* [Orders API](services/orders-api.md) — owns the order lifecycle and checkout.
* [Payments API](services/payments-api.md) — captures charges and refunds.

# Datasets

* [Orders database](datasets/orders-db.md) — Postgres schema of record.

# Decisions

* [Adopt OKF for shared knowledge](decisions/use-okf.md) — why this repo uses OKF.
* [Event-driven service communication](decisions/event-driven.md) — why services publish events.

# Runbooks

* [Payment failures runbook](runbooks/payment-failures.md) — respond to failed charges.

# Metrics

* [Checkout conversion](metrics/checkout-conversion.md) — paid orders over started checkouts.
