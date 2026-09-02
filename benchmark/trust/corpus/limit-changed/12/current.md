---
type: Reference
title: "Netherby failover timing"
description: "How long a Netherby failover takes end to end, and which step dominates it."
tags: [netherby, failover, timing]
status: stable
generated: { by: human:okf-bench, at: 2026-09-02T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-02T09:00:00Z }
stale_after: 2027-10-31
---
# Netherby failover timing

Failover is dominated by waiting for the dead holder's lease to expire; every
other step is milliseconds.

## The arithmetic

A lease is held for 4 minutes, so a holder that dies immediately after renewing
leaves the resource unavailable for that long, and the expected wait is half of
it. Deployments that cannot tolerate the wait run a standby that renews on a
shorter schedule against a second lease.

## After expiry

The claim is one write, and the winner replays its journal before accepting
traffic, typically under two seconds.
