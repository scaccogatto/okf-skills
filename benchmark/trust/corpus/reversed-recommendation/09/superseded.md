---
type: Reference
title: "Cobble producer guidance"
description: "What a Cobble producer should do while the collector is unreachable."
tags: [cobble, producers, guidance]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-05T09:00:00Z }
stale_after: 2026-08-28
---
# Cobble producer guidance

**Recommended: buffer.** A producer that cannot reach the collector should hold
events in memory and send them when the collector returns.

## The trade

| Behaviour | Events lost | Producer memory |
|---|---|---|
| buffer | none, up to the buffer | grows during an outage |
| drop | all events during the outage | flat |

Buffering keeps a short collector outage invisible in the data, which matters
because most outages are shorter than the buffer is deep.

## Sizing the buffer

Size it for the longest outage you intend to survive at your event rate, and
make it bounded: an unbounded buffer converts a collector outage into a producer
outage.
