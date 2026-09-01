---
type: Reference
title: Selkie bucket replication defaults
description: Replication factor applied to a new Selkie store bucket and the durability it targets.
tags: [selkie, store, replication]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-25T09:00:00Z }
stale_after: 2026-10-15
---
# Selkie bucket replication defaults

A new Selkie store bucket is created with a **replication factor of 3**. Three
copies are placed in distinct failure domains before a write is acknowledged, and
a bucket keeps that factor for its lifetime unless it is explicitly rewritten.

## What three copies buy

The placement rule is one copy per domain, so the bucket survives the loss of any
single domain with no read impact and the loss of two with degraded reads.

| Factor | Domains lost tolerated | Storage cost |
|---|---|---|
| 3 | 1 fully, 2 degraded | 3.0x |
| 5 | 2 fully | 5.0x |

## Changing it

`replication` at create time takes any odd value the placement policy can satisfy.
Changing the factor afterwards is a bucket rewrite, not a metadata edit, and is
scheduled as a background job.
