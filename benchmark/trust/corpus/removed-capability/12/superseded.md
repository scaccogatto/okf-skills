---
type: Reference
title: "Wrenfield time-travel queries"
description: "Querying a Wrenfield table as it was at an earlier time."
tags: [wrenfield, queries, snapshots]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-06T09:00:00Z }
stale_after: 2026-06-28
---
# Wrenfield time-travel queries

A **time-travel query** runs against the table as it was at a chosen timestamp:
`SELECT ... AS OF '2026-01-01T00:00:00Z'`.

## What it can reach

| Window | Available |
|---|---|
| Within retention (7 days) | yes |
| Older than retention | no |

Undo records are kept for seven days, and a query naming a timestamp outside
that window fails rather than returning the current state, which would be the
dangerous answer.

## Cost

A time-travel query reads undo records in addition to the table, so it costs
roughly twice a normal query at the far end of the window and very little near
the present.
