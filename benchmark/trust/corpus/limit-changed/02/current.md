---
type: Reference
title: "Fenwick ledger compaction"
description: "How Fenwick compaction merges sealed ledger segments and what it costs per pass."
tags: [fenwick, ledger, compaction]
status: stable
generated: { by: human:okf-bench, at: 2026-06-28T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-28T09:00:00Z }
stale_after: 2027-08-31
---
# Fenwick ledger compaction

Compaction merges sealed segments into a single output segment and drops
entries superseded by a later write to the same key.

## Cost of a pass

A segment holds 3072 entries, so a pass over sixteen sealed segments reads
49152 entries and writes however many survive deduplication. The pass is
scheduled off the append path and holds no lock on the open segment.

## Scheduling

Compaction runs when the sealed-segment count crosses `compaction.trigger`,
default sixteen. A pass may be cancelled mid-way; its output is discarded and
the input segments are untouched.
