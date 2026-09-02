---
type: Reference
title: "Corvid deployment patterns"
description: "The deployment patterns a Corvid mesh supports, and which one fits a given latency and isolation target."
tags: [corvid, mesh, patterns]
status: stable
generated: { by: human:okf-bench, at: 2026-06-30T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-30T09:00:00Z }
stale_after: 2027-07-31
---
# Corvid deployment patterns

Three patterns, chosen by what the deployment is optimising for.

## Latency

The recommended topology is multi-region: members sit next to their consumers,
and the digest gossip protocol keeps convergence independent of the worst link.

## Isolation

A relay pair at the boundary terminates the mesh protocol and forwards only
subscribed channels. Choose it when a partition must not propagate, not for
latency.

## Cost

A single small mesh with a relay to everything else is the cheapest pattern and
is the right default for non-interactive workloads.
