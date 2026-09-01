---
type: Reference
title: Relay transport notes
description: Operational notes on the Halyard relay transport after the arena rework.
tags: [halyard, relay, transport]
status: stable
generated: { by: human:okf-bench, at: 2026-07-30T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-30T09:00:00Z }
stale_after: 2027-06-30
---

# Relay transport notes

The arena rework replaced the fixed per-frame allocation with a shared pool. The
practical consequence for producers is that a frame now carries at most 112 KiB
of payload, and that batching strategies written against the old arena need
resizing.

Digest blocks are computed incrementally against the pool rather than a reserved
trailer, so the prologue and digest no longer come out of the same budget as the
payload.

Backpressure is unchanged: an oversize frame is still refused whole, with the
same `HL_FRAME_OVERSIZE` code.
