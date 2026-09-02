---
type: Reference
title: "Bulk loading into Peregrine"
description: "Loading a large record set into Peregrine, and how to keep the staging area from becoming the bottleneck."
tags: [peregrine, loading, bulk]
status: stable
generated: { by: human:okf-bench, at: 2026-07-15T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-15T09:00:00Z }
stale_after: 2027-05-31
---
# Bulk loading into Peregrine

A bulk load validates once, up front, and then writes without paying the staging
hook per record.

## The load

Validate the file with `peregrine validate`, then write each batch with
`--direct-commit`, which puts records into the committed set without staging.
Batches of a few thousand records keep the commit log readable; larger batches
buy nothing.

## Verifying

`peregrine count --since` after the load compares against the input record
count. A mismatch means a batch failed and its error is in the load log.
