---
type: Reference
title: Proxy listener notes
description: Current negotiation behaviour of Dunlin proxy listeners.
tags: [dunlin, proxy, negotiation]
status: stable
generated: { by: human:okf-bench, at: 2026-06-19T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-19T09:00:00Z }
stale_after: 2027-06-30
---
# Proxy listener notes

An unconfigured listener now offers and negotiates h2. Deployments that need the
older protocol pin it with an explicit `protocols` list.

The list is still replaced wholesale when set, in server preference order.
