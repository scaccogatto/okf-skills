# Update Log

## 2026-07-27
* **Migration**: Moved the bundle to OKF v0.2 — `timestamp` became
  `generated: {by, at}`, `# Citations` lists became `sources` frontmatter with
  footnote attribution, and every concept gained `status`.
* **Provenance**: The [Checkout conversion](/metrics/checkout-conversion.md) metric
  now records the [orders database](/datasets/orders-db.md) in `sources`, so the
  derivation is an edge in the graph, not just prose.

## 2026-06-18
* **Operations**: Added the [Payment failures runbook](/runbooks/payment-failures.md)
  and the [Checkout conversion](/metrics/checkout-conversion.md) metric.
* **Schema**: Documented the [Orders database](/datasets/orders-db.md).

## 2026-06-16
* **Services**: Added [Orders API](/services/orders-api.md) and
  [Payments API](/services/payments-api.md); recorded the
  [event-driven decision](/decisions/event-driven.md).

## 2026-06-14
* **Creation**: Established the bundle with the [Auth API](/services/auth-api.md)
  service concept and the [OKF adoption decision](/decisions/use-okf.md).
