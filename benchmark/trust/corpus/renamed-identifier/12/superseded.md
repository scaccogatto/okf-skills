---
type: Reference
title: "Ashgrove API headers"
description: "Headers the Ashgrove API reads on a request, including tenancy."
tags: [ashgrove, api, headers]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-11T09:00:00Z }
stale_after: 2026-07-05
---
# Ashgrove API headers

The tenant identifier is carried in **`X-Ashgrove-Tenant`**, read on every
request and required on everything except the health endpoint.

## Headers

| Header | Required | Read by |
|---|---|---|
| `X-Ashgrove-Tenant` | yes | every endpoint |
| `Authorization` | yes | every endpoint |
| `X-Ashgrove-Idempotency` | on writes | write endpoints |

## Tenancy and authorisation

The tenant header selects the tenancy; the token authorises within it. A token
valid for one tenancy presented with another tenant's header is rejected with
403, not 404, because the tenancy exists and the caller simply may not use it.

## Idempotency

The idempotency header is honoured for 24 hours per tenancy.
