---
type: Reference
title: "Netherby resource adapters"
description: "Writing an adapter that puts a resource under Netherby coordination."
tags: [netherby, adapters, integration]
status: stable
generated: { by: human:okf-bench, at: 2026-09-27T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-27T09:00:00Z }
stale_after: 2027-12-31
---
# Netherby resource adapters

An adapter mediates between a resource and the coordinator, and is the only
component that needs to understand both.

## Token validation

Validation is recommended at the coordinator, so the adapter presents each write
for authorisation and applies it once the coordinator confirms the token is
current. Resources therefore need no token storage of their own, which is what
makes adapters possible for resources nobody can modify.

## Failure handling

A rejected write is surfaced to the caller unchanged; the adapter never retries
on its own, because a retry after rejection is precisely the write fencing is
meant to stop.
