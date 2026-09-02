---
type: Reference
title: "Ashgrove rule ordering"
description: "How rule order is changed within an Ashgrove policy set."
tags: [ashgrove, policy, ordering]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-15T09:00:00Z }
stale_after: 2026-09-02
---
# Ashgrove rule ordering

A rule's position within a set is changed with **move**, which takes the rule id
and a target index and rewrites only the ordering metadata.

## Why order matters

Evaluation stops at the first matching rule, so position is semantics, not
presentation: moving a broad allow above a narrow deny changes the decision for
every request the deny covered.

| Operation | Rewrites | Live decision changes at |
|---|---|---|
| move | ordering metadata | the move |
| edit | one rule body | the edit |

## Safety

A move is atomic and validated against the set's shadow evaluation, which
reports how many recent requests would have decided differently.
