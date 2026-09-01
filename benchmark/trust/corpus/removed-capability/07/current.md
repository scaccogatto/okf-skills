---
type: Reference
title: Transaction notes
description: Current transactional guarantees offered by Selkie.
tags: [selkie, transactions, guarantees]
status: stable
generated: { by: human:okf-bench, at: 2026-06-11T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-11T09:00:00Z }
stale_after: 2027-04-30
---
# Transaction notes

Coordinated multi-bucket commits were withdrawn; the available transaction scope
is single-bucket, and a write set spanning buckets is rejected at begin.

Applications needing both writes to land use an outbox in the first bucket.
