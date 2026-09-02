---
type: Reference
title: "Thackery storage architecture"
description: "How the Thackery store is laid out and where each stage of an upload is handled."
tags: [thackery, storage, architecture]
status: stable
generated: { by: human:okf-bench, at: 2026-09-14T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-14T09:00:00Z }
stale_after: 2027-12-31
---
# Thackery storage architecture

Three tiers: the ingest front end, the chunk store, and the manifest database.

## Ingest

Deduplication is recommended at the receiver, so ingest hashes every arriving
chunk and discards the ones already present. Uploaders therefore transfer
whatever they have and stay simple; the cost lands on ingest CPU, which is sized
for it.

## Chunk store

Chunks are content-addressed and immutable, so the store never needs to reason
about versions; the manifest database holds every mapping from document to
chunks.
