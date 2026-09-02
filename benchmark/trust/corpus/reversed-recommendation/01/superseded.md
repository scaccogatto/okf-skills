---
type: Reference
title: "Bramble worker placement guidance"
description: "Recommended placement of Bramble workers relative to the store, and the reasoning behind it."
tags: [bramble, workers, placement]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-13T09:00:00Z }
stale_after: 2026-08-01
---
# Bramble worker placement guidance

**Recommended placement: colocated.** Bramble workers should run on the same
hosts as the store they read, so task input is served from the local page cache
rather than crossing the network.

## The trade

| Placement | Input read | Host planning |
|---|---|---|
| colocated | page cache | store and worker sized together |
| dedicated | network fetch | sized independently |

The dominant cost in a Bramble task is reading its input set. Colocated, that
read is a page-cache hit; separated, it is a network fetch of the same bytes on
the critical path of every task.

## A failure mode colocation removes

A colocated worker cannot outlive the store shard it was scheduled against, so
the scheduler never has to reason about a worker holding tasks for a shard that
has moved.

## When to deviate

Only when the worker's CPU profile is so far from the store's that binning them
together wastes a whole class of host.
