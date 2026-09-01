---
type: Reference
title: Access control notes
description: Current policy resolution for Selkie access decisions.
tags: [selkie, access, policy]
status: stable
generated: { by: human:okf-bench, at: 2026-09-13T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-13T09:00:00Z }
stale_after: 2027-09-30
---
# Access control notes

Resolution now makes the account policy decisive: a bucket may narrow it but not
depart from it, so an account-wide deny holds everywhere.

Auditing an account's exposure therefore no longer requires reading every bucket.
