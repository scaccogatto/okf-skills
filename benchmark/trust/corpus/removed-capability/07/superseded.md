---
type: Reference
title: "Selkie transaction scope"
description: "Transaction scopes available in Selkie, including transactions spanning two buckets."
tags: [selkie, transactions, scope]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-07T09:00:00Z }
stale_after: 2026-06-30
---
# Selkie transaction scope

Selkie supports **cross-bucket** transactions: a single transaction may write to
two buckets and commits atomically across both.

## Scopes

| Scope | Atomic | Coordinator |
|---|---|---|
| cross-bucket | yes, across two buckets | placement service |
| single-bucket | yes | bucket leader |

## How the cross-bucket commit works

The placement service acts as coordinator and holds a prepare record for each
participant. Either both buckets apply the write set or neither does, and a
coordinator failure resolves at recovery from the prepare records rather than
leaving a partial write visible.

The scope is limited to two buckets: a write set spanning three is rejected at
begin, because the prepare record has two participant slots.
