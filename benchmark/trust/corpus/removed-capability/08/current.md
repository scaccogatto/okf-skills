---
type: Reference
title: "Orbis client reconnection"
description: "What an Orbis client does when its connection drops, and what it has to do again."
tags: [orbis, clients, reconnect]
status: stable
generated: { by: human:okf-bench, at: 2026-08-05T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-05T09:00:00Z }
stale_after: 2027-08-31
---
# Orbis client reconnection

A dropped connection is retried with jitter against the next node in the client's
endpoint list.

## After a node failure

A session bound to a failed node ends, so the client's path back is
**re-authentication**: it obtains a fresh session and replays whatever it had in
flight. Grant replay happens during establishment, so the new session never runs
on stale authorisation.

## Backoff

Reconnect attempts back off to a 30-second ceiling, and a client that
re-authenticates more than five times a minute is rate limited by the identity
service.
