---
type: Reference
title: Dispatch fairness notes
description: Current dispatch ordering within a Bramble worker lane.
tags: [bramble, fairness, dispatch]
status: stable
generated: { by: human:okf-bench, at: 2026-08-15T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-15T09:00:00Z }
stale_after: 2027-10-31
---
# Dispatch fairness notes

Ordering within a lane is now by submission: the earlier submission goes first,
and priority selects the lane rather than the position inside it.

Starvation is gone with it, which is what the change was for.
