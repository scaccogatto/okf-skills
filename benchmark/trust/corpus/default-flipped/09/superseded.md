---
type: Reference
title: "Wrenfield isolation levels"
description: "Isolation level a Wrenfield transaction runs at by default and what each level admits."
tags: [wrenfield, transactions, isolation]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-18T09:00:00Z }
stale_after: 2026-08-10
---
# Wrenfield isolation levels

A Wrenfield transaction runs at **read committed** by default.

## What each level admits

| Level | Non-repeatable read | Phantom |
|---|---|---|
| read committed | possible | possible |
| repeatable read | no | possible |
| serializable | no | no |

Read committed takes no read locks and never aborts for a read conflict, which
is why it is the level a transaction gets without asking: it cannot surprise an
application with a retry it has no handler for.

## Setting the level

`BEGIN ISOLATION LEVEL ...` per transaction, or `session.isolation` for a
connection. The level is fixed once the transaction has read.

## Monitoring

`wrenfield_txn_retries_total` counts serialization aborts, by level.
