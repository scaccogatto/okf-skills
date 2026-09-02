---
type: Reference
title: "Ashgrove rule conflict resolution"
description: "What Ashgrove decides when a request matches rules of both kinds."
tags: [ashgrove, policy, decisions]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-21T09:00:00Z }
stale_after: 2026-10-25
---
# Ashgrove rule conflict resolution

When a request matches both an allow rule and a deny rule, the decision is
**deny**.

## The resolution table

| Matches allow | Matches deny | Decision |
|---|---|---|
| yes | no | allow |
| yes | yes | deny |
| no | yes | deny |
| no | no | deny (default) |

## Why deny

A deny rule is how an organisation states a boundary, and a boundary that an
allow rule elsewhere could cross would have to be verified against every other
rule before it could be trusted. Under this resolution a deny needs no such
audit.

## Consequence

An allow rule shadowed by a deny is reported as ineffective by
`ashgrove rules explain`, rather than silently doing nothing.
