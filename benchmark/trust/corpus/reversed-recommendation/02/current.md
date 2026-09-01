---
type: Reference
title: Ingest client notes
description: Current guidance for clients writing into Selkie.
tags: [selkie, clients, guidance]
status: stable
generated: { by: human:okf-bench, at: 2026-08-21T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-21T09:00:00Z }
stale_after: 2027-08-31
---
# Ingest client notes

With the commit path rewritten around a shared durability round trip, the
recommended write shape is streamed: clients send records as they arrive and let
the server group them.

Client-side batching now mostly adds latency without removing overhead.
