---
type: Reference
title: "The Pellworm invalidation API"
description: "Invalidating Pellworm entries from an application, by key and by tag."
tags: [pellworm, cache, api]
status: stable
generated: { by: human:okf-bench, at: 2026-09-04T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-04T09:00:00Z }
stale_after: 2027-11-30
---
# The Pellworm invalidation API

Two calls: `invalidate_key(key)` and `invalidate_tag(tag)`, both asynchronous
and both idempotent.

## Overlap

Where an entry is covered by both kinds, **the key rule** governs, which is what
lets a targeted correction survive a release-wide flush. Write the key rule
after the tag rule or before it; ordering does not matter, only scope does.

## Propagation

An invalidation reaches every node within one gossip round, typically under 200
ms, and `pellworm rules explain` shows which rule governs a given entry.
