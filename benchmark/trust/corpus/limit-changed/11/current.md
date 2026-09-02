---
type: Reference
title: "Wrenfield schema migrations"
description: "Running schema migrations against Wrenfield tables without taking them offline."
tags: [wrenfield, schema, migrations]
status: stable
generated: { by: human:okf-bench, at: 2026-08-18T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-18T09:00:00Z }
stale_after: 2027-09-30
---
# Wrenfield schema migrations

Migrations run online: readers see the old schema until the swap, writers see
both.

## Sizing a migration

A table holds at most 256 columns, so the migration plan is small enough to
render in the review comment, one line per column. Migrations that add and drop
in the same plan are applied add-first, which is what keeps the column count
under the ceiling mid-migration.

## Rollback

A migration is reversible until the swap; after it, rollback is a second
migration.
