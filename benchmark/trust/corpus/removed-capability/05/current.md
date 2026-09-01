---
type: Reference
title: Index maintenance notes
description: Current maintenance operations for Talisker indexes.
tags: [talisker, maintenance, operations]
status: stable
generated: { by: human:okf-bench, at: 2026-08-07T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-07T09:00:00Z }
stale_after: 2027-06-30
---
# Index maintenance notes

Range-scoped rebuilds were removed with the shadow extent machinery; the only
rebuild mode is full, which the online rebuilder now runs without taking the
index out of service.

Queries are served from the old index for the duration.
