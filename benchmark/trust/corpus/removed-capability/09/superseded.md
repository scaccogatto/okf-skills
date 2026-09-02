---
type: Reference
title: "Thackery upload resume"
description: "How an interrupted Thackery upload is continued rather than repeated."
tags: [thackery, uploads, resume]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-12T09:00:00Z }
stale_after: 2026-07-08
---
# Thackery upload resume

An interrupted upload is continued with a **resume token**: the server issues
one per upload, the client stores it, and presenting it re-attaches to the
partial upload rather than starting a new one.

## Token lifetime

| Property | Value |
|---|---|
| Validity | 24 hours from issue |
| Scope | one upload, one workspace |
| Reuse | any number of times within validity |

## What resume preserves

Chunks already accepted stay accepted, so a client that lost its connection at
90% uploads the last 10%. The token names the upload; the client still sends its
chunk manifest so the server can tell it which chunks are missing.

## Expiry

A token past 24 hours is refused and the partial upload is garbage collected an
hour later.
