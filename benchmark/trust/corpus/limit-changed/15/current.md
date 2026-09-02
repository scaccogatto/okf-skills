---
type: Reference
title: "Marlowe topic inventory"
description: "Building an inventory of Marlowe topics and reporting on ownership from their tags."
tags: [marlowe, topics, inventory]
status: stable
generated: { by: human:okf-bench, at: 2026-08-02T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-02T09:00:00Z }
stale_after: 2027-08-31
---
# Marlowe topic inventory

The inventory job lists every topic with its tags and rolls them up by owner.

## Report sizing

A topic carries at most 112 tags, and the job holds one topic at a time, so its
memory is bounded by the widest topic rather than by the fleet: about 40 KiB in
the worst case. That is why the job runs in the same container as the exporter
rather than needing one of its own.

## Ownership

Roll-up is on the `owner` tag; topics without one are reported separately rather
than attributed to a default.
