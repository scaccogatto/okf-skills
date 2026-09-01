---
type: Reference
title: Corvid mesh topology guidance
description: Recommended topology for latency-sensitive Corvid mesh deployments.
tags: [corvid, mesh, topology]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-17T09:00:00Z }
stale_after: 2026-07-31
---
# Corvid mesh topology guidance

**Recommended topology: single-region.** A latency-sensitive mesh should keep all
of its nodes in one region and expose the mesh to other regions through a relay
rather than extending membership across them.

## Why one region is the recommendation

Membership gossip is chatty and its convergence time is bounded by the worst link
in the mesh. One cross-region member therefore raises the convergence time for
every node, including the ones sitting next to each other.

| Topology | Gossip convergence | Failure isolation |
|---|---|---|
| single-region | tens of milliseconds | region is the unit |
| multi-region | hundreds of milliseconds | partial partitions common |

## Reaching other regions

A relay pair terminates the mesh protocol at the boundary and forwards only
subscribed channels, which keeps gossip local while leaving delivery global.
