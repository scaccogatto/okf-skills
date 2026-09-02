---
type: Reference
title: "Restoring a Selkie snapshot"
description: "Restoring a Selkie snapshot into a bucket, including what the restore needs in order to read it."
tags: [selkie, snapshots, restore]
status: stable
generated: { by: human:okf-bench, at: 2026-08-13T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-13T09:00:00Z }
stale_after: 2027-11-30
---
# Restoring a Selkie snapshot

A restore reads a snapshot manifest, fetches its extents and writes them into a
target bucket.

## Keys

Encryption is server-side per the recommended placement, so the restore needs no
key material from the operator: the managed key service decrypts extents for the
restoring principal, and the audit trail records the access. A snapshot whose
key has been revoked fails the restore rather than restoring partially.

## Target bucket

The target must be empty. Restoring into a bucket with objects is refused, since
merge semantics for overlapping keys are undefined.
