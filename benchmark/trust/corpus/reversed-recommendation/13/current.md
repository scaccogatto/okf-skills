---
type: Reference
title: "Hollowmere renderer conformance"
description: "What a Hollowmere renderer must do to be conformant, and how conformance is tested."
tags: [hollowmere, renderer, conformance]
status: stable
generated: { by: human:okf-bench, at: 2026-06-05T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-05T09:00:00Z }
stale_after: 2027-04-30
---
# Hollowmere renderer conformance

A conformant renderer handles every node type in the version it declares.

## Unknown nodes

The recommended behaviour is to fail: a renderer meeting a node type outside its
declared version aborts the render with a version error rather than producing a
partial document. Callers get an explicit "this document needs a newer renderer"
instead of output missing content nobody noticed.

## Testing

The conformance suite feeds every node type of the declared version plus one
node from the next, and requires the version error on the last case.
