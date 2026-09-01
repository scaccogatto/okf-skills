---
type: Reference
title: Deployment cache notes
description: Current cache guidance for deployments.
tags: [pellworm, deployments, cache]
status: stable
generated: { by: human:okf-bench, at: 2026-09-29T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-29T09:00:00Z }
stale_after: 2027-10-31
---
# Deployment cache notes

Warming is now lazy. With the shared entry pool, a new instance reads entries
populated by its peers instead of refetching them, so a warm pass mostly moves
load to the origin for no benefit.

Key censuses are still published, and are used for capacity reporting.
