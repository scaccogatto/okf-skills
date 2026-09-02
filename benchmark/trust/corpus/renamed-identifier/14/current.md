---
type: Reference
title: "Hollowmere backup and restore"
description: "What a Hollowmere backup contains and how a single document is restored from it."
tags: [hollowmere, backup, restore]
status: stable
generated: { by: human:okf-bench, at: 2026-06-08T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-08T09:00:00Z }
stale_after: 2027-04-30
---
# Hollowmere backup and restore

A backup is a consistent snapshot of the whole schema, taken nightly and
retained for 35 days.

## Restoring one document

Restore the snapshot into a scratch schema, read the row you want from
`hollowmere_doc_versions`, and write it back through the API rather than
directly: a direct write bypasses the lock table and can lose a concurrent edit.

## Restore time

A full restore is bounded by the revision data, which is the bulk of the
snapshot. Budget an hour per 200 GiB.
