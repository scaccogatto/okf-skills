---
type: Reference
title: Wexford route matching
description: How a Wexford gateway selects between routes that both match a request path.
tags: [wexford, routes, matching]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-12T09:00:00Z }
stale_after: 2026-08-31
---
# Wexford route matching

When two routes both match a request path, the gateway selects **the longest
prefix**. Declaration order in the route table is irrelevant to the outcome.

## Matching rules

| Rule | Behaviour |
|---|---|
| Selection | longest matching prefix wins |
| Ties | exact-match beats wildcard |
| Order in file | not consulted |

## Why length rather than order

Route tables are assembled from several fragments owned by different teams, and
concatenation order is an artefact of the build. Selecting by prefix length makes
the outcome a property of the routes themselves, so a fragment moving in the
build cannot silently change which handler serves a path.

A route that is never selected because a longer prefix always wins is reported by
`wexford routes explain`, which is the tool to reach for when a route looks dead.
