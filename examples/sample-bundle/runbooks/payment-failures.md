---
type: Runbook
title: Payment failures runbook
description: Diagnose and mitigate a spike in declined or failed charges.
tags: [oncall, payments, incident]
status: stable
generated: { by: human:sam, at: "2026-06-18T07:30:00Z" }
stale_after: 2026-12-31
---

# Trigger

Charge success rate (tracked by the
[Checkout conversion metric](/metrics/checkout-conversion.md)) drops below 95%
for 5 minutes, or `order.failed` events spike.

# Diagnose

1. Check [Payments API](/services/payments-api.md) `/healthz` and processor
   status page — is this us or upstream?
2. Tail charge attempts in the [Orders database](/datasets/orders-db.md):
   ```sql
   SELECT decline_code, count(*) FROM charges
   WHERE created_at > now() - interval '15 min' AND status = 'failed'
   GROUP BY 1 ORDER BY 2 DESC;
   ```
3. A single dominant `decline_code` → processor-side. Many varied codes → likely
   our integration (expired key, bad idempotency).

# Mitigate

* **Processor outage:** enable the queue-and-retry flag; orders go `pending`, not
  `failed`, and drain when the processor recovers.
* **Expired signing key:** rotate via [Auth API](/services/auth-api.md) and
  redeploy Payments.

# Verify

Success rate recovers above 99% and the `pending` backlog drains to zero.
