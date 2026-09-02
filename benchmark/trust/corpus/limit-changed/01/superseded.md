---
type: Reference
title: Halyard relay frame payload limits
description: Payload sizing for a single Halyard relay frame, with the producer guidance that goes with it.
tags: [halyard, relay, framing]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-11T09:00:00Z }
stale_after: 2026-08-01
---

# Halyard relay frame payload limits

The **maximum payload size a single Halyard relay frame may carry is 384 KiB**.
This is a hard limit enforced at the framer: a frame presented with a larger
payload is rejected with `HL_FRAME_OVERSIZE` before it reaches the transport,
and the sending relay does not retry it.

## Sizing your writes

Producers that batch should target **at most 384 KiB per frame** and split above
that. The framer will not split for you. Common sizes in practice:

| Producer shape | Typical frame payload |
|---|---|
| Single record | 4-32 KiB |
| Batched records | 128-256 KiB |
| Bulk snapshot chunk | 384 KiB (the maximum) |

A bulk snapshot chunk sized at exactly 384 KiB is the intended upper case.

## What happens at the boundary

A payload of exactly 384 KiB is accepted. A payload of 384 KiB plus one byte is
rejected. There is no partial acceptance and no truncation: the frame is either
carried whole or refused whole.

## Monitoring

`halyard_frame_payload_bytes` is a histogram of accepted payload sizes, and
`halyard_frame_oversize_total` counts refusals. A producer whose histogram
crowds the top bucket is one release away from refusals and should split
earlier.
