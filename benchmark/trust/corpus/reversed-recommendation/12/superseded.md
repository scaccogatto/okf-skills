---
type: Reference
title: "Thackery deduplication guidance"
description: "Where chunk deduplication belongs and what each placement costs."
tags: [thackery, deduplication, guidance]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-23T09:00:00Z }
stale_after: 2026-09-12
---
# Thackery deduplication guidance

**Recommended: uploader.** The uploader should hash its chunks and ask which
ones are already held before transferring anything.

## The comparison

| Placement | Bytes on the wire | Receiving CPU |
|---|---|---|
| uploader | only new chunks | hashing for verification only |
| receiver | every chunk | hashing on every upload |

For the workloads this guidance came from, most of an upload is chunks the store
already holds: an uploader-side check turns a full upload into a manifest
exchange and a handful of chunk transfers.

## The exchange

The uploader sends chunk hashes, gets back the subset that is wanted, and
transfers only those.
