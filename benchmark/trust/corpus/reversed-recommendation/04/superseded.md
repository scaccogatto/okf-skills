---
type: Reference
title: "Wexford retry placement guidance"
description: "Which layer should retry idempotent routes, and what the choice does to load under failure."
tags: [wexford, retries, guidance]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-22T09:00:00Z }
stale_after: 2026-07-15
---
# Wexford retry placement guidance

**Recommended layer: edge.** Retries for idempotent routes belong at the edge,
which already knows the route's idempotency declaration and can retry without
the caller having to.

## The comparison

| Layer | Retry cost | Budget scope |
|---|---|---|
| edge | one hop | shared, enforced |
| caller | full round trip | per caller, unenforced |

The edge sees the failure closest to the origin, so its retry costs one hop
instead of a full round trip, and it applies one budget across everyone rather
than trusting every integration to implement backoff correctly.

## Configuring it

`retry.idempotent` on the route enables it, and the route's declared idempotency
key is what makes the retry safe. A route without a declared key is never
retried, whatever the setting says.
