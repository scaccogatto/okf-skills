---
type: Reference
title: "Hollowmere default resolution"
description: "Which default a Hollowmere field takes when the document and its template disagree."
tags: [hollowmere, templates, defaults]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-18T09:00:00Z }
stale_after: 2026-09-07
---
# Hollowmere default resolution

Where a document and its template both define a default for a field, the
**template default** is used.

## Resolution

| Defined in | Used |
|---|---|
| template only | template |
| document only | document |
| both | template |

## Why the template wins

A template is how an organisation states what a class of document must look
like, and a document able to override its template's defaults would make the
template advisory. Fields a document may legitimately vary are declared
`overridable` in the template, and those resolve the other way.

## Inspecting

`hollowmere doc explain --field` prints the effective default and its source.
