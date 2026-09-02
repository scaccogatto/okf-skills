---
type: Reference
title: "Selkie consistency model"
description: "What Selkie guarantees for readers and writers, and where the guarantees stop."
tags: [selkie, consistency, guarantees]
status: stable
generated: { by: human:okf-bench, at: 2026-06-11T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-11T09:00:00Z }
stale_after: 2027-04-30
---
# Selkie consistency model

Reads are strongly consistent within a bucket and monotonic across buckets.

## Transactions

The available transaction scope is **single-bucket**: a write set spanning
buckets is rejected at begin. Applications that need two writes to land together
put both in one bucket, or write an outbox record in the first bucket and let a
worker apply the second.

## Readers

A reader sees a bucket's writes in commit order and never observes a partial
write set. Across buckets, a reader may see the second bucket lag the first.
