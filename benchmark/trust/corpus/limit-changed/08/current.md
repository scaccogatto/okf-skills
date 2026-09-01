---
type: Reference
title: Stream coordination notes
description: Operational notes on Juniper stream coordination after the ownership record change.
tags: [juniper, stream, coordination]
status: stable
generated: { by: human:okf-bench, at: 2026-08-11T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-11T09:00:00Z }
stale_after: 2027-11-30
---
# Stream coordination notes

The ownership record now carries per-shard lease metadata, which leaves room for
28 shards in a single stream. Wide ingest topologies are expected to use several
streams instead.

Failed splits are still atomic: the stream keeps its previous shard count.
