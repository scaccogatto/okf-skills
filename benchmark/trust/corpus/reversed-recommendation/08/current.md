---
type: Reference
title: Mesh topology notes
description: Current topology guidance for Corvid mesh deployments.
tags: [corvid, mesh, deployments]
status: stable
generated: { by: human:okf-bench, at: 2026-06-30T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-30T09:00:00Z }
stale_after: 2027-07-31
---
# Mesh topology notes

Since gossip moved to the digest protocol, convergence no longer tracks the worst
link, and the recommended topology for latency-sensitive deployments is
multi-region: members sit next to their consumers.

Relays remain available and are now an isolation choice rather than a latency
requirement.
