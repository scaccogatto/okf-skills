---
type: Reference
title: "Sizing a Tamarisk broker"
description: "Sizing memory, disk and network for a Tamarisk broker from its topic set."
tags: [tamarisk, broker, sizing]
status: stable
generated: { by: human:okf-bench, at: 2026-09-22T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-22T09:00:00Z }
stale_after: 2027-10-31
---
# Sizing a Tamarisk broker

Size from the topic set: topic count decides metadata memory, and retention
decides everything else.

## Disk

Topics are created on-disk without an explicit `durability`, so plan disk for
the full retention window of every topic plus 20% for compaction headroom. A
broker that runs out of disk stops accepting publishes rather than dropping
messages.

## Memory

Memory is the page pool plus roughly 8 MiB of metadata per topic. The page pool
is sized to hold a few seconds of publish traffic, not the retention window.
