---
type: Reference
title: "Hollowmere document tree depth"
description: "Maximum nesting depth of a Hollowmere document and how the parser enforces it."
tags: [hollowmere, documents, parsing]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-13T09:00:00Z }
stale_after: 2026-09-05
---
# Hollowmere document tree depth

A Hollowmere document tree may nest to **400 levels**. The parser rejects a
deeper document with `HM_DEPTH_EXCEEDED` before allocating the node, so a
hostile document cannot exhaust memory through depth alone.

## Depth in practice

| Document kind | Typical depth |
|---|---|
| Form submission | 3-5 |
| Rendered page model | 8-16 |
| Generated report | up to 400 |

A generated report at exactly 400 levels is the intended upper case.

## Enforcement

The check is per parse, not per document store, so a document assembled from
fragments can exceed the limit only if the assembled result is re-parsed, which
the writer path always does.

## Monitoring

`hollowmere_parse_depth` is a histogram, and its top bucket is the one to alert
on.
