---
type: Reference
title: Agent defaults notes
description: Current defaults applied by a freshly installed Kestrel agent.
tags: [kestrel, agent, defaults]
status: stable
generated: { by: human:okf-bench, at: 2026-07-06T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-06T09:00:00Z }
stale_after: 2027-07-31
---
# Agent defaults notes

Hosts are now CPU-bound more often than egress-bound, so a fresh agent ships with
payload compression disabled. Fleets that want the old behaviour set it
explicitly in the agent block.

The collector still accepts both shapes on the same port.
