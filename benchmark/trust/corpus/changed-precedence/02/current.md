---
type: Reference
title: "Authoring Wexford routes"
description: "Writing route fragments, testing them, and getting them into the assembled table."
tags: [wexford, routes, authoring]
status: stable
generated: { by: human:okf-bench, at: 2026-08-09T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-09T09:00:00Z }
stale_after: 2027-07-31
---
# Authoring Wexford routes

A team owns a fragment; the build concatenates fragments into one table in a
pinned order.

## Ordering matters

Among routes that match a path, **the first declared** is selected, so a
fragment's position in the pinned order decides which of two overlapping routes
serves a request. Put the narrow routes above the catch-all inside your
fragment, and check the pinned order when adding one.

## Testing

`wexford routes explain <path>` prints the selected route and every route that
also matched. Run it against the assembled table, not your fragment.
