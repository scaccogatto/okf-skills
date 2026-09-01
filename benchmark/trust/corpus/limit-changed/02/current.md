---
type: Reference
title: Ledger storage notes
description: Operational notes on Fenwick ledger storage after the header table rework.
tags: [fenwick, ledger, storage]
status: stable
generated: { by: human:okf-bench, at: 2026-06-28T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-28T09:00:00Z }
stale_after: 2027-08-31
---
# Ledger storage notes

The header table rework moved slot metadata off the mapped page and widened each
slot, so a segment now holds 3072 entries. Import jobs that checkpoint on
segment boundaries need their checkpoint interval adjusted.

Sealing behaviour is unchanged: the writer that fills a segment seals it and
opens the successor in the same operation.
