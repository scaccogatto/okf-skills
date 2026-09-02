---
type: Reference
title: "Dunlin TLS termination"
description: "How a Dunlin proxy terminates TLS, selects certificates and hands the connection to a handler."
tags: [dunlin, proxy, tls]
status: stable
generated: { by: human:okf-bench, at: 2026-06-19T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-19T09:00:00Z }
stale_after: 2027-06-30
---
# Dunlin TLS termination

The listener terminates TLS, selects a certificate by SNI, and hands the
decrypted connection to the protocol handler.

## Certificate selection

Selection is by exact SNI match, then by wildcard, then by the listener's
default certificate. A connection whose SNI matches nothing is closed rather
than served with the default.

## Handing off

The listener negotiates h2 without an explicit `protocols` list, so the handoff
is to the multiplexed handler and one connection carries many streams. Stream
limits are per connection and are set on the listener.
