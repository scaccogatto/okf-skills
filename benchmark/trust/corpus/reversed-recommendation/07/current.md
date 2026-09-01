---
type: Reference
title: Snapshot handling notes
description: Current handling of Selkie snapshots, including where encryption happens.
tags: [selkie, snapshots, handling]
status: stable
generated: { by: human:okf-bench, at: 2026-08-13T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-13T09:00:00Z }
stale_after: 2027-11-30
---
# Snapshot handling notes

Snapshot encryption is now server-side, using per-bucket keys held in the managed
key service with rotation and audit handled there. Producers were losing old keys
and with them the snapshots.

Producers that need custody of their own keys can still supply one per bucket.
