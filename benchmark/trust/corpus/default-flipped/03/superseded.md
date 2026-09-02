---
type: Reference
title: "Dunlin proxy listener protocol negotiation"
description: "Protocol a Dunlin proxy listener negotiates by default and how the ALPN list is built."
tags: [dunlin, proxy, listeners]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-24T09:00:00Z }
stale_after: 2026-07-01
---
# Dunlin proxy listener protocol negotiation

A Dunlin proxy listener negotiates **http/1.1 by default**. The ALPN list
offered to clients is built from the listener block, and an unconfigured
listener offers exactly one entry.

## Negotiation table

| Listener config | ALPN offered | Negotiated |
|---|---|---|
| unconfigured | http/1.1 | http/1.1 |
| `protocols: [h2, http/1.1]` | both | client's choice |

A single-entry list makes the negotiated protocol a property of configuration
rather than of client behaviour, which is what makes a packet capture on the
listener interpretable without knowing the client.

## Overriding it

Setting `protocols` replaces the list wholesale. Ordering in that list is the
server preference order and is honoured against clients offering several.

## Monitoring

`dunlin_alpn_negotiated` is a counter by protocol and listener.
