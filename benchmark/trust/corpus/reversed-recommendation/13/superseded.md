---
type: Reference
title: "Hollowmere unknown node guidance"
description: "What a renderer should do when it meets a node type it does not know."
tags: [hollowmere, renderer, guidance]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-05T09:00:00Z }
stale_after: 2026-06-20
---
# Hollowmere unknown node guidance

**Recommended: skip.** A renderer meeting a node type it does not know should
skip the node, render its children, and continue.

## Why skipping

Documents outlive renderers: a document written by a newer editor is opened by
an older renderer routinely, and skipping is what makes that document mostly
readable rather than not readable at all.

| Behaviour | Older renderer, newer document |
|---|---|
| skip | renders, minus the unknown node |
| fail | renders nothing |

## Reporting

A skipped node is counted and reported in the render result, so a caller that
cares can detect degradation without the render failing.
