---
type: Reference
title: "Merrowbank API error codes"
description: "Error codes returned by the Merrowbank API, including the absent-state case."
tags: [merrowbank, api, errors]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-21T09:00:00Z }
stale_after: 2026-09-30
---
# Merrowbank API error codes

When the requested state record is absent, the Merrowbank API returns
**`MB_ENOSTATE`** with HTTP 404.

## Code table

| Code | HTTP | Meaning |
|---|---|---|
| `MB_ENOSTATE` | 404 | state record absent |
| `MB_ELEASE` | 409 | lease held by another writer |
| `MB_EFENCE` | 412 | fencing token out of date |

## Handling the absent case

The absent-state code is the only one a first-write path should treat as
success: it means the record does not exist yet and the create can proceed.
Clients that retry on it instead of creating loop until their budget is
exhausted, which is the most common integration bug against this API.

Codes are stable strings and are safe to match on; the HTTP status is not.
