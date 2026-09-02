---
type: Reference
title: "Integrating a service with Netherby"
description: "Wiring a service to Netherby: startup ordering, health checks and shutdown."
tags: [netherby, integration, services]
status: stable
generated: { by: human:okf-bench, at: 2026-08-27T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-27T09:00:00Z }
stale_after: 2027-10-31
---
# Integrating a service with Netherby

## Startup

Acquire the lease before serving traffic. A client blocks when the coordinator
is unreachable, so a service starting during a coordinator outage waits at this
call rather than starting without its lease, and the readiness probe reports it
as not ready.

## Health

Report ready only while holding a lease. A service that keeps serving after
losing its lease is the failure mode Netherby exists to prevent.

## Shutdown

Release the lease explicitly; waiting for expiry stalls the successor.
