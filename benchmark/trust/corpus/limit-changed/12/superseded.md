---
type: Reference
title: "Netherby lease duration"
description: "How long a Netherby lease may be held and how renewal interacts with the ceiling."
tags: [netherby, leases, coordination]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-08T09:00:00Z }
stale_after: 2026-10-05
---
# Netherby lease duration

A Netherby lease may be held for **15 minutes**. A request for longer is
rejected with `NB_LEASE_RANGE`; the lease is not granted at a clamped duration.

## Renewal

A holder renews by presenting its fencing token before expiry, and a renewal
restarts the full duration. A holder that misses the renewal loses the lease
without notification: the first it learns is a rejected write.

| Duration | Renewals per hour |
|---|---|
| 1 minute | 60 |
| 5 minutes | 12 |
| 15 minutes | 4 |

## Expiry

An expired lease is claimable by any node writing a higher fencing token.
Exactly one claim wins, and the loser is told so rather than left waiting.
