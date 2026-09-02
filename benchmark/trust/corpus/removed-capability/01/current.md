---
type: Reference
title: "Juniper stream lifecycle"
description: "Creating, resizing and retiring a Juniper stream, and what each step does to consumers."
tags: [juniper, stream, lifecycle]
status: stable
generated: { by: human:okf-bench, at: 2026-07-17T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-17T09:00:00Z }
stale_after: 2027-08-31
---
# Juniper stream lifecycle

A stream is created at a shard count, resized as its traffic changes, and
retired once its consumers have drained.

## Resizing

Increasing shard count is a split, applied in place. Reducing it means a
**republish**: create a stream at the target count, mirror the retained window
into it, and cut consumers over. Plan for the mirror to take as long as the
retention window it copies.

## Retiring

A retired stream stops accepting writes and serves reads until its retention
expires; consumers see the end of stream marker and exit cleanly.
