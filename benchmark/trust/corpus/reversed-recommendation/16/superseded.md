---
type: Reference
title: "Tamarisk absent consumer guidance"
description: "What a topic should do with messages when no consumer is attached."
tags: [tamarisk, topics, guidance]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-14T09:00:00Z }
stale_after: 2026-08-26
---
# Tamarisk absent consumer guidance

**Recommended: retain.** A topic whose consumer is not attached should keep
messages until the consumer returns or retention expires.

## Why retain

A consumer restart is routine, and a topic that discards during one turns a
deploy into data loss. Retention bounds the cost: the topic holds at most its
retention window regardless of how long the consumer stays away.

| Behaviour | Consumer restart | Broker memory |
|---|---|---|
| retain | no loss | grows to the retention window |
| discard | loses the window | flat |

## Sizing

Set retention from the longest consumer absence you intend to survive, and size
broker memory for the topics that use it.
