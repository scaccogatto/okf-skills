---
type: Reference
title: "Selkie ingest write guidance"
description: "Recommended write shape for Selkie ingest clients and how it interacts with commit costs."
tags: [selkie, ingest, writes]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-04T09:00:00Z }
stale_after: 2026-09-01
---
# Selkie ingest write guidance

**Recommended write shape: batched.** Ingest clients should accumulate records
and submit them as one write rather than sending each record as it arrives.

## Why the shape matters

Every write pays a fixed commit cost regardless of size: a placement decision, a
durability round trip and a metadata update.

| Shape | Commits per 10k records | Overhead share |
|---|---|---|
| batched (1k per write) | 10 | ~4% |
| streamed (1 per write) | 10000 | ~70% |

## Sizing a batch

Target a batch that fills within a second of arrival at steady-state rate, and
flush on the timer when it does not. A batch held for latency it cannot recover
is worse than the overhead it saves.

## Failure handling

A batch is all-or-nothing, so a client retrying a failed batch must retry the
whole batch and rely on the record keys for idempotence.
