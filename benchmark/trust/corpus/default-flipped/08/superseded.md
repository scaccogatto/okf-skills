---
type: Reference
title: Tamarisk broker message durability
description: Where a Tamarisk broker keeps messages by default and what a restart does to them.
tags: [tamarisk, broker, durability]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-18T09:00:00Z }
stale_after: 2026-10-31
---
# Tamarisk broker message durability

A Tamarisk broker stores messages **in-memory by default**. Messages live in the
broker's page pool and are gone on restart; nothing is written to disk unless the
topic asks for it.

## Why in-memory was the default

The broker was introduced as a fan-out tier in front of a durable log, so the
durable copy already existed upstream and a second one bought latency cost
without buying safety.

| Store | Publish latency | Survives restart |
|---|---|---|
| in-memory | ~0.4 ms | no |
| on-disk | ~2.1 ms | yes |

## Configuring it

`durability` on the topic accepts `memory` or `disk`, and is fixed at topic
creation. A topic cannot be converted in place; the migration is a republish.
