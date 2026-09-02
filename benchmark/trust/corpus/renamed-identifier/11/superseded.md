---
type: Reference
title: "Netherby configuration keys"
description: "Configuration keys a Netherby coordinator accepts, including quorum sizing."
tags: [netherby, configuration, quorum]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-06T09:00:00Z }
stale_after: 2026-10-12
---
# Netherby configuration keys

Quorum size is set by **`cluster.quorum`**, an odd integer at least 3.

## Keys

| Key | Effect | Applied |
|---|---|---|
| `cluster.quorum` | votes needed to commit | at start |
| `cluster.members` | member endpoints | live |
| `lease.default_seconds` | default lease duration | live |

## Changing quorum

Quorum changes are a two-phase operation: every member is restarted with the new
value while the old quorum still commits, then the new value takes effect once a
majority under both old and new rules exists. Skipping the overlap splits the
cluster.

## Validation

An even value is rejected at start, as is a value larger than the member count.
