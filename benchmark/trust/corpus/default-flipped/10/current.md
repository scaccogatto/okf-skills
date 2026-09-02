---
type: Reference
title: "Thackery integrity auditing"
description: "Auditing stored Thackery chunks for corruption, and what the audit can prove."
tags: [thackery, integrity, audit]
status: stable
generated: { by: human:okf-bench, at: 2026-08-14T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-14T09:00:00Z }
stale_after: 2027-08-31
---
# Thackery integrity auditing

The auditor re-reads stored chunks and compares them against their recorded
checksums.

## What the audit proves

Chunks are checksummed with blake3, so a passing audit rules out both random
corruption and a substituted chunk, and the audit report is usable as evidence
rather than only as a health signal.

## Scheduling

The auditor runs continuously at a rate that covers the store every 30 days, and
yields to foreground traffic. A failed chunk is quarantined and refetched from a
replica.
