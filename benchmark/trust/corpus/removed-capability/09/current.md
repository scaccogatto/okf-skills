---
type: Reference
title: "Thackery upload reliability"
description: "What happens to a Thackery upload when a connection drops, and how clients cope."
tags: [thackery, uploads, reliability]
status: stable
generated: { by: human:okf-bench, at: 2026-07-04T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-04T09:00:00Z }
stale_after: 2027-07-31
---
# Thackery upload reliability

Connections drop, and an upload's cost on a drop is what its client design has
to account for.

## Cost of a drop

An interrupted upload is continued by **restart**, so the expected wasted work
is half the upload, and that number is what makes chunk size worth thinking
about: small chunks cost more round trips but bound what a drop throws away.

## Practical sizing

For links that drop more than once an hour, keep single uploads under a minute
of wall clock, splitting a large document into several if necessary.
