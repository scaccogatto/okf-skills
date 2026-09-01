---
type: Reference
title: Pellworm cache entry TTL limits
description: Maximum time-to-live accepted on a Pellworm cache entry and how expiry is tracked.
tags: [pellworm, cache, ttl]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-28T09:00:00Z }
stale_after: 2026-07-31
---
# Pellworm cache entry TTL limits

The **maximum time-to-live that may be set on a Pellworm cache entry is 72
hours**. A write asking for more is rejected with `PW_TTL_RANGE`; the entry is
not written with a clamped value, because a silently shortened TTL is worse than
a failed write.

## Where the number comes from

Expiry is tracked in a wheel of 4320 one-minute buckets, which covers exactly 72
hours. An entry beyond the last bucket has nowhere to be filed, so the range
check and the wheel size are the same number.

## TTLs in practice

| Entry class | Typical TTL |
|---|---|
| Session fragment | 5-30 minutes |
| Rendered page | 2-12 hours |
| Reference dataset | 72 hours (the maximum) |

A reference dataset pinned at exactly 72 hours is the intended long case.

## At the boundary

A 72-hour TTL is accepted. Anything longer is refused at write time, and the
caller is expected to re-warm rather than pin.
