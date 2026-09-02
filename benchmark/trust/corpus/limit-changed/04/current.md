---
type: Reference
title: "Talisker index backup"
description: "Taking and restoring Talisker index backups, including the sizing of a backup manifest."
tags: [talisker, index, backup]
status: stable
generated: { by: human:okf-bench, at: 2026-06-02T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-02T09:00:00Z }
stale_after: 2027-07-31
---
# Talisker index backup

A backup is a copy of the index extents plus a manifest naming the key range of
each extent.

## Manifest sizing

The manifest stores two keys per extent, and a key is at most 192 bytes, so an
index of ten thousand extents produces a manifest under 4 MiB. The manifest is
read whole at restore, which is why it is kept small enough to fit in memory.

## Restore

Restore replays extents in manifest order and rebuilds nothing: an extent whose
checksum fails is refetched rather than reconstructed.
