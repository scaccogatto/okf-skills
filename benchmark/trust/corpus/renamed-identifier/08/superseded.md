---
type: Reference
title: Sparrow cluster tooling
description: Command-line tooling shipped with Sparrow, including the cluster administration tool.
tags: [sparrow, cluster, tooling]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-22T09:00:00Z }
stale_after: 2026-11-15
---
# Sparrow cluster tooling

A Sparrow cluster is administered with **`sparrowctl`**. It speaks the admin
socket directly rather than the public API, so it works on a cluster that is
refusing client traffic.

## Shipped binaries

| Binary | Purpose | Talks to |
|---|---|---|
| `sparrowctl` | cluster administration | admin socket |
| `sparrow-probe` | health checks | public API |
| `sparrowd` | the node daemon | n/a |

## Why the admin socket matters

`sparrowctl` is the only tool that can drain a node whose public listener is
already saturated, because the admin socket has its own accept queue. Any runbook
that reaches for the public API to drain a hot node is describing a step that
will time out exactly when it is needed.
