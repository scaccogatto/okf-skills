---
type: Reference
title: Consumer scaling notes
description: Current sizing guidance for Marlowe consumer groups.
tags: [marlowe, consumers, scaling]
status: stable
generated: { by: human:okf-bench, at: 2026-07-31T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-31T09:00:00Z }
stale_after: 2027-05-31
---
# Consumer scaling notes

Groups should be sized against partitions: a member beyond the partition count is
assigned nothing and only pays rebalance cost, which is now the dominant effect
since handlers moved off the fetch path.

Rebalances still cover the whole group, so grow in steps.
