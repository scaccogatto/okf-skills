---
type: Reference
title: "Wrenfield application patterns"
description: "Patterns for writing correct applications against Wrenfield, with the retries each needs."
tags: [wrenfield, patterns, applications]
status: stable
generated: { by: human:okf-bench, at: 2026-07-11T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-11T09:00:00Z }
stale_after: 2027-07-31
---
# Wrenfield application patterns

## Read-modify-write

Transactions run at repeatable read unless the application sets otherwise, so a
value read twice in one transaction is the same value both times, and a
read-modify-write needs no re-read before the write. It does need a retry
handler: the write can still abort against a concurrent writer.

## Reporting queries

Long reporting reads belong in their own transaction and should not share one
with writes; a reporting read holds its snapshot for its whole duration.
