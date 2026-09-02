---
type: Reference
title: "Thackery workspace upload concurrency"
description: "How many uploads a Thackery workspace runs at once and what happens past the ceiling."
tags: [thackery, uploads, concurrency]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-14T09:00:00Z }
stale_after: 2026-07-20
---
# Thackery workspace upload concurrency

A single Thackery workspace runs **at most 128 concurrent uploads**. The 129th
is queued in the client rather than refused, so a workspace never fails an
upload for concurrency alone.

## Where uploads spend their time

| Phase | Share of wall clock |
|---|---|
| Chunk hashing | 15% |
| Transfer | 70% |
| Commit | 15% |

With 128 in flight, a workspace saturates a gigabit link on files above 8 MiB
and is latency-bound below that.

## Queueing

The client queue is unbounded and FIFO. An upload cancelled while queued never
starts; one cancelled in flight is cleaned up server-side within a minute.

## Monitoring

`thackery_uploads_active` is a gauge and `thackery_upload_queue_depth` its
companion. A queue depth that never drains means the workspace is producing
faster than the link carries.
