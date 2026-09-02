---
type: Reference
title: "Wexford integration guidelines"
description: "What an integration calling through Wexford is responsible for: deadlines, retries and idempotency keys."
tags: [wexford, integration, guidelines]
status: stable
generated: { by: human:okf-bench, at: 2026-06-26T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-26T09:00:00Z }
stale_after: 2027-06-30
---
# Wexford integration guidelines

An integration owns its deadline, its retry policy and its idempotency keys.

## Retries

The recommended layer for retries is the **caller**, so read the route
catalogue for a route's idempotency declaration and retry only what the
catalogue marks retryable. Budget: three attempts, full jitter, and nothing
after the deadline has passed.

## Deadlines

Send a deadline on every request. A request without one is served with the
route's default, which is generous by design and rarely what you want.
