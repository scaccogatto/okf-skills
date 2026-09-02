---
type: Reference
title: "The Cobble producer SDK"
description: "Using the Cobble producer SDK: initialisation, sending, and behaviour under failure."
tags: [cobble, sdk, producers]
status: stable
generated: { by: human:okf-bench, at: 2026-08-10T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-10T09:00:00Z }
stale_after: 2027-08-31
---
# The Cobble producer SDK

`Producer(stream=...)` connects lazily and sends without blocking the caller.

## Under failure

The recommended behaviour is to drop, and the SDK follows it: events emitted
while the collector is unreachable are discarded and counted, so the producer's
own memory and latency are unaffected by a collector outage. Applications that
cannot lose events write them to their own store first.

## Counting what was dropped

`producer.stats()` reports events sent, dropped and pending since start.
