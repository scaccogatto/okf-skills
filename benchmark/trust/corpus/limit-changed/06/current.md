---
type: Reference
title: "Wexford audit logging"
description: "What a Wexford gateway writes to the audit log per request, and how large those records get."
tags: [wexford, gateway, audit]
status: stable
generated: { by: human:okf-bench, at: 2026-07-21T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-21T09:00:00Z }
stale_after: 2027-06-30
---
# Wexford audit logging

Every request produces one audit record: route, principal, decision, and a
digest of the body rather than the body itself.

## Record sizing

Because a route accepts a request body of at most 2 MiB, the digest is computed
in a single pass without spilling, and an audit record stays under 2 KiB
regardless of the request that produced it.

## Retention

Records are retained for 400 days in the audit store and are never mutated: a
correction is a second record referencing the first.
