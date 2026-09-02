---
type: Reference
title: "Orbis schema reference"
description: "Tables in the Orbis schema, including the one holding session state."
tags: [orbis, schema, sessions]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-11T09:00:00Z }
stale_after: 2026-09-15
---
# Orbis schema reference

Session state lives in **`orbis_sessions`**, keyed by session id with the tenant
id as the first column of the covering index.

## Tables

| Table | Rows | Retention |
|---|---|---|
| `orbis_sessions` | one per live session | 30 days after close |
| `orbis_identities` | one per principal | indefinite |
| `orbis_grants` | one per grant | until revoked |

## Querying session state

The session table is written on every request that touches a session, so
analytic queries against it belong on a replica. The covering index makes
tenant-first lookups cheap and session-id-first lookups a scan, which is the
opposite of what most new queries assume.

Rows are soft-deleted at close and removed by the retention job.
