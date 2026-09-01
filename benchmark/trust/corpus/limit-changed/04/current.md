---
type: Reference
title: Index node layout
description: Current layout of Talisker index nodes after the slot-packing change.
tags: [talisker, index, layout]
status: stable
generated: { by: human:okf-bench, at: 2026-06-02T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-02T09:00:00Z }
stale_after: 2027-07-31
---
# Index node layout

Slot packing now stores the ordering suffix inline, which leaves 192 bytes for
the key in each slot. Composite natural keys written against the old geometry
have to be hashed or shortened.

Comparison semantics are unchanged: keys are ordered as raw bytes, and an
over-long key is refused at insert.
