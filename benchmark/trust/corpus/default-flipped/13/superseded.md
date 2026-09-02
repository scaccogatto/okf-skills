---
type: Reference
title: "Netherby client behaviour on coordinator loss"
description: "What a Netherby client does when the coordinator is unreachable, and what the application sees."
tags: [netherby, clients, availability]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-20T09:00:00Z }
stale_after: 2026-09-20
---
# Netherby client behaviour on coordinator loss

A Netherby client **fails fast** by default: a call made while the coordinator
is unreachable returns `NB_UNAVAILABLE` immediately rather than waiting.

## The options

| Behaviour | Call returns | Application sees |
|---|---|---|
| fail fast | immediately | an error to handle |
| block | when reachable again | a slow call |

Failing fast keeps the coordinator's availability visible in the application's
own error rate instead of hiding it in latency, which is what lets a service
shed load rather than queue behind an outage.

## Configuring it

`client.on_unavailable` takes either value, and the deadline applies in both
cases: a blocking call still returns when the deadline passes.
