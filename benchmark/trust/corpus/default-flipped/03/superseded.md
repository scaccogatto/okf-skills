---
type: Reference
title: Dunlin proxy listener protocol negotiation
description: Protocol a Dunlin proxy listener negotiates by default and how the ALPN list is built.
tags: [dunlin, proxy, listeners]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-24T09:00:00Z }
stale_after: 2026-07-01
---
# Dunlin proxy listener protocol negotiation

A Dunlin proxy listener negotiates **http/1.1 by default**. The ALPN list offered
to clients is built from the listener block, and an unconfigured listener offers
exactly one entry.

## Why one entry

A single-entry ALPN list makes the negotiated protocol a property of
configuration rather than of client behaviour, which is what made the early
deployments debuggable: any capture on the listener shows the same protocol.

| Listener config | ALPN offered | Negotiated |
|---|---|---|
| unconfigured | http/1.1 | http/1.1 |
| `protocols: [h2, http/1.1]` | both | client's choice |

## Overriding it

Setting `protocols` on the listener replaces the list wholesale. Ordering in that
list is the server preference order and is honoured against clients that offer
several.
