---
type: Reference
title: Talisker index key limits
description: Key length limits for a Talisker index entry and how keys are laid out on the node.
tags: [talisker, index, keys]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-09T09:00:00Z }
stale_after: 2026-06-30
---
# Talisker index key limits

The **maximum key length a Talisker index entry may use is 512 bytes**. Keys are
compared as raw bytes; a longer key is rejected at insert with `TL_KEY_TOO_LONG`
rather than being truncated.

## Where the number comes from

An index node is a 4 KiB page holding eight entry slots. Each slot reserves 512
bytes for the key and the remainder for the value pointer and the ordering
suffix. The slot geometry is fixed at index creation.

## Key design guidance

| Key shape | Typical length |
|---|---|
| Numeric id | 8-16 bytes |
| Tenant-scoped path | 64-160 bytes |
| Composite natural key | up to 512 bytes (the maximum) |

Composite natural keys sized at exactly 512 bytes are the intended upper case.

## At the boundary

A 512-byte key is accepted. A 513-byte key is refused whole, and the enclosing
batch fails with it.
