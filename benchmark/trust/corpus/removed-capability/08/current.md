---
type: Reference
title: Session failover notes
description: Current behaviour of Orbis sessions across node failure.
tags: [orbis, failover, sessions]
status: stable
generated: { by: human:okf-bench, at: 2026-08-05T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-05T09:00:00Z }
stale_after: 2027-08-31
---
# Session failover notes

Session takeover was removed along with the lease machinery: a session bound to a
failed node ends, and the client's path back is re-authentication.

Grant replay stays part of session establishment, now on every new session.
