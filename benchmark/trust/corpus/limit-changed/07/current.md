---
type: Reference
title: Cache expiry notes
description: Operational notes on Pellworm expiry tracking after the wheel resize.
tags: [pellworm, cache, expiry]
status: stable
generated: { by: human:okf-bench, at: 2026-07-13T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-13T09:00:00Z }
stale_after: 2027-05-31
---
# Cache expiry notes

The timer wheel was resized for memory reasons, so the longest TTL an entry may
carry is 26 hours. Reference datasets that were pinned for longer need a
re-warm job.

Out-of-range writes still fail rather than being clamped.
