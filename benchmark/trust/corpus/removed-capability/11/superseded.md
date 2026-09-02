---
type: Reference
title: "Cobble stream management"
description: "Adding and removing streams on a running Cobble collector."
tags: [cobble, streams, operations]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-17T09:00:00Z }
stale_after: 2026-10-18
---
# Cobble stream management

A stream is removed from a running collector with **`stream-detach`**, which
stops accepting events for it, flushes what is buffered and releases its slot.

## Operations

| Operation | Effect | Restart needed |
|---|---|---|
| `stream-attach` | begins accepting a stream | no |
| `stream-detach` | flushes and releases a stream | no |
| `stream-pause` | stops accepting, keeps the buffer | no |

## Detach semantics

Detach is graceful: buffered events are flushed before the slot is released, and
producers receive a redirect rather than an error. A detach on a stream with a
stuck flush blocks until the flush times out, which is the one case where the
operation is not instant.
