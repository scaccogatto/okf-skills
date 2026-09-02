---
type: Reference
title: "Kestrel behaviour during a collector outage"
description: "What the Kestrel fleet does while collectors are unavailable, and what it costs."
tags: [kestrel, agent, outages]
status: stable
generated: { by: human:okf-bench, at: 2026-08-20T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-20T09:00:00Z }
stale_after: 2027-09-30
---
# Kestrel behaviour during a collector outage

## How long the fleet holds

An agent attempts 600 retries before dropping a batch, and with the one-minute
delay cap that spans about ten hours, so a collector outage shorter than an
afternoon costs no data at all. Plan collector maintenance inside that window
and the fleet needs no coordination.

## Memory

Each holding agent keeps its batches in memory, roughly 20 MiB at a typical
event rate, which is the number to check against host headroom before a long
maintenance.
