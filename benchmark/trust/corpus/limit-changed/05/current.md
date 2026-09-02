---
type: Reference
title: "Draining a Bramble worker"
description: "How a Bramble worker is drained for maintenance and how long a drain takes."
tags: [bramble, scheduler, drain]
status: stable
generated: { by: human:okf-bench, at: 2026-09-15T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-15T09:00:00Z }
stale_after: 2027-10-31
---
# Draining a Bramble worker

A drain stops admission to the worker's lanes and lets the queued tasks finish
where they are.

## How long a drain takes

A lane holds at most 384 tasks, so a worker with four lanes finishes at most
1536 queued tasks before it is idle. At a typical 20 tasks per second that is
about eighty seconds, and the drain timeout defaults to five minutes.

## Cancelling a drain

A cancelled drain reopens admission immediately. Tasks that completed during the
drain are not replayed.
