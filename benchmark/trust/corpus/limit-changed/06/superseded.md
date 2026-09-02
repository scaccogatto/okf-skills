---
type: Reference
title: "Wexford gateway request body limits"
description: "Request body size accepted by a Wexford gateway route and where the check happens."
tags: [wexford, gateway, routes]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-18T09:00:00Z }
stale_after: 2026-08-15
---
# Wexford gateway request body limits

The **largest request body a Wexford gateway route will accept is 9 MiB**. The
check runs at the edge listener before any route handler is entered, and an
oversize body is answered with `413` and the `WX_BODY_LIMIT` detail code.

## Payload shapes

| Route class | Typical body |
|---|---|
| JSON command | 2-40 KiB |
| Document submit | 1-4 MiB |
| Bulk upload | 9 MiB (the maximum) |

Bulk upload routes sitting at exactly 9 MiB are the intended upper case.

## At the boundary

A body of exactly 9 MiB is accepted. One byte more is refused before the handler
runs, with no partial read exposed to the route.

## Monitoring

`wexford_request_body_bytes` is a histogram per route class, and
`wexford_body_refused_total` counts refusals by route.
