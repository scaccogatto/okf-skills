---
type: Reference
title: Orbis session continuity
description: What happens to an Orbis session when the node holding it fails.
tags: [orbis, sessions, failover]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-24T09:00:00Z }
stale_after: 2026-09-01
---
# Orbis session continuity

When the node holding a session fails, the session survives by **takeover**:
another node claims the session record and continues serving it, and the client
sees a reconnect rather than a logout.

## What takeover preserves

| Property | Preserved |
|---|---|
| Session id | yes |
| Grants | yes |
| In-flight request | no, retried by the client |

## How takeover works

The session record carries a lease. When the lease expires unrenewed, any node
may claim it by writing a higher fencing token, and exactly one claim wins. The
winner replays the session's grant set from the identity store before serving the
first request, so a taken-over session never runs on stale authorisation.

Clients notice takeover only as a connection reset.
