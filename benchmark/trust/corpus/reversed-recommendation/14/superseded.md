---
type: Reference
title: "Netherby fencing token guidance"
description: "Where a fencing token should be checked, and what the placement protects against."
tags: [netherby, fencing, guidance]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-19T09:00:00Z }
stale_after: 2026-10-20
---
# Netherby fencing token guidance

**Recommended: at the resource.** The resource being protected should check the
fencing token on every write and reject anything below the highest token it has
seen.

## What the placement protects

A holder can be paused between checking its lease and issuing a write. Only the
resource sees the write itself, so only the resource can reject the write from a
holder whose lease expired mid-operation.

| Checked at | Protects against a paused holder |
|---|---|
| resource | yes |
| coordinator | no, the check happens before the write |

## Implementing it

Store the highest token seen alongside the data, compare on every write, and
reject rather than queue.
