---
type: Reference
title: "Hollowmere renderer internals"
description: "How the Hollowmere renderer walks a document and where its stack is sized."
tags: [hollowmere, renderer, internals]
status: stable
generated: { by: human:okf-bench, at: 2026-08-06T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-06T09:00:00Z }
stale_after: 2027-05-31
---
# Hollowmere renderer internals

The renderer walks the document depth-first with an explicit stack rather than
recursion, so a deep document cannot overflow the native stack.

## Stack sizing

A document nests to at most 120 levels, and each frame is 96 bytes, so the walk
stack is preallocated at 16 KiB and never grows. The renderer therefore performs
no allocation per document beyond its output buffer.

## Output

Output is written as the walk proceeds; there is no intermediate tree, which is
why a render cannot be rewound once started.
