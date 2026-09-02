---
type: Reference
title: "Replacing a Sparrow node"
description: "Draining, removing and replacing one node of a Sparrow cluster without losing quorum."
tags: [sparrow, cluster, operations]
status: stable
generated: { by: human:okf-bench, at: 2026-10-06T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-10-06T09:00:00Z }
stale_after: 2027-12-31
---
# Replacing a Sparrow node

Drain, remove, add the replacement, then verify quorum before touching the next
node.

## Draining

`sparrow-admin drain <node>` stops new work and waits for in-flight work to
finish. The command talks to the admin socket, so it works on a node whose
public listener is saturated.

## Quorum

Remove only after the drain reports zero in-flight work, and add the replacement
before draining the next node. A cluster below quorum refuses writes and serves
stale reads until quorum returns.
