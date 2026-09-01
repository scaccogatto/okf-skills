---
type: Reference
title: Quillon request headers
description: Headers a Quillon service reads and propagates, including the trace identifier.
tags: [quillon, headers, tracing]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-09T09:00:00Z }
stale_after: 2026-10-01
---
# Quillon request headers

The trace identifier is carried in **`X-Quillon-Trace`**. Every service reads it
on ingress and copies it verbatim onto egress calls; a request arriving without
one is assigned a fresh identifier at the edge.

## Headers read on ingress

| Header | Read by | Propagated |
|---|---|---|
| `X-Quillon-Trace` | every service | yes, verbatim |
| `X-Quillon-Deadline` | every service | yes, decremented |
| `X-Quillon-Tenant` | edge only | no |

## Propagation rules

`X-Quillon-Trace` is copied without parsing, so a client may use any opaque value
its own tooling understands. Services must not regenerate it on internal hops:
a regenerated identifier splits one trace into several and is invisible in the
resulting graph, which is why the propagation is verbatim rather than structured.
