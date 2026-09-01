---
type: Reference
title: Talisker index rebuild modes
description: Rebuild modes a Talisker index supports, including rebuilding a single key range.
tags: [talisker, index, rebuild]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-19T09:00:00Z }
stale_after: 2026-08-31
---
# Talisker index rebuild modes

A Talisker index supports a **partial** rebuild over a single key range: the
range is rebuilt from the base table while the rest of the index keeps serving
queries.

## Modes

| Mode | Scope | Queries during rebuild |
|---|---|---|
| partial | one key range | served outside the range |
| full | whole index | served from the old index |

## How the partial rebuild works

The range is copied into a shadow extent, verified against the base table, then
swapped in under the index lock. Only the affected range is unavailable, and only
for the duration of the swap.

This is the mode to reach for after a range-scoped corruption or a bulk delete: a
full rebuild of a large index costs hours where a partial costs minutes.
