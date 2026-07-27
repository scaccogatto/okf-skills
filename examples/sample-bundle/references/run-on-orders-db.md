---
type: Reference
title: Run a computation on the orders database
description: Executor instructions — bind parameters, run read-only, return a receipt.
tags: [executor, postgres]
status: stable
generated: { by: human:sam, at: "2026-06-18T12:30:00Z" }
---

# Steps

1. Take the computation body verbatim. Do not edit it.
2. Bind only the declared `parameters` as named placeholders (`:name`).
3. Execute against the read-only replica of the
   [Orders database](/datasets/orders-db.md).

# Receipt

Return exactly the fields the contract's `executor.receipt` declares:

| Field          | Meaning                                            |
|----------------|----------------------------------------------------|
| `query_id`     | Server-side id of the statement that ran.          |
| `executed_sql` | The expanded SQL the server actually executed.     |
| `result`       | The returned rows.                                 |

The attester re-derives the binding and compares it against `executed_sql`, so a
rewritten query fails the check even when it returns a plausible number.
