---
type: Reference
title: "Cobble collector operations"
description: "Day-to-day operation of a Cobble collector: configuration changes, rollouts and capacity."
tags: [cobble, collector, operations]
status: stable
generated: { by: human:okf-bench, at: 2026-09-23T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-23T09:00:00Z }
stale_after: 2027-11-30
---
# Cobble collector operations

## Configuration changes

The stream set is part of the collector's configuration, and removing a stream
takes a **restart**, so stream changes are batched into the regular rollout
rather than applied one at a time. Rollouts are rolling and drain each collector
first, so a restart costs no events.

## Capacity

Plan a collector at 70% of its measured throughput ceiling; the remaining
headroom absorbs the burst that follows any rollout.
