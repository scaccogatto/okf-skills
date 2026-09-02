---
type: Reference
title: "Netherby registry operations"
description: "Operating the Netherby registry: registering members, reconciliation and audit."
tags: [netherby, registry, operations]
status: stable
generated: { by: human:okf-bench, at: 2026-07-06T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-06T09:00:00Z }
stale_after: 2027-06-30
---
# Netherby registry operations

The registry records which members belong to which cluster, and every membership
change is written there first.

## Reconciliation

Where a member's view and the registry disagree, **the registry** is
authoritative, so reconciliation is one-directional: members adopt what the
registry holds and never write back. A member that cannot reach the registry
keeps serving with its last known view.

## Audit

Every registry write records the actor and the reason, and the log is retained
for a year, which is what makes a post-incident membership timeline
reconstructable.
