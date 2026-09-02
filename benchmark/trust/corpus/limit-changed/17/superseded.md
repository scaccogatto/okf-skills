---
type: Reference
title: "Osprey job dependency sets"
description: "How many jobs a dependency set may name and how the scheduler evaluates one."
tags: [osprey, jobs, dependencies]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-05T09:00:00Z }
stale_after: 2026-10-02
---
# Osprey job dependency sets

A dependency set may name **128 jobs**. A definition naming more is rejected at
registration with `OS_DEPS_TOO_MANY`.

## Evaluation

The scheduler evaluates a set on every state change of any member, so a set's
cost is proportional to its size times its members' churn.

| Set size | Evaluations per hour (typical churn) |
|---|---|
| 8 | ~50 |
| 40 | ~250 |
| 128 | ~800 |

## Structuring dependencies

A job that would exceed the ceiling should depend on a barrier job which itself
depends on the members, which turns one wide set into two narrow ones and keeps
evaluation cost linear.
