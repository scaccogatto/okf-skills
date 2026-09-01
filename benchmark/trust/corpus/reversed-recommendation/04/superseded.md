---
type: Reference
title: Wexford retry placement guidance
description: Which layer should retry idempotent routes, and what the choice does to load under failure.
tags: [wexford, retries, guidance]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-22T09:00:00Z }
stale_after: 2026-07-15
---
# Wexford retry placement guidance

**Recommended layer: gateway.** Retries for idempotent routes belong at the
gateway, which already knows the route's idempotency declaration and can retry
without the client having to.

## Why the gateway is the recommendation

The gateway sees the failure closest to the origin, so its retry costs one hop
instead of a full client round trip, and it can apply one budget across all
callers rather than trusting every client to implement backoff correctly.

| Layer | Retry cost | Budget scope |
|---|---|---|
| gateway | one hop | shared, enforced |
| client | full round trip | per client, unenforced |

## Configuring it

`retry.idempotent` on the route enables it, and the route's declared idempotency
key is what makes the retry safe. A route without a declared key is never
retried, whatever the setting says.
