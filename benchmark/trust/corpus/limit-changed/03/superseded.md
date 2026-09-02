---
type: Reference
title: "Corvid mesh channel subscription limits"
description: "Concurrent subscription capacity of a Corvid mesh channel and the fan-out it implies."
tags: [corvid, mesh, subscriptions]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-03T09:00:00Z }
stale_after: 2026-09-01
---
# Corvid mesh channel subscription limits

The **maximum number of concurrent subscriptions a Corvid mesh channel may
carry is 240**. The 241st subscribe call is rejected at the channel head with
`CV_SUB_LIMIT`, and the mesh does not queue it behind an existing slot.

## Fan-out shapes in practice

| Deployment | Subscriptions per channel |
|---|---|
| Single service | 2-8 |
| Regional fan-out | 40-120 |
| Broadcast channel | 240 (the maximum) |

A broadcast channel sitting at exactly 240 subscriptions is the intended upper
case.

## At the boundary

Subscription 240 is accepted. Subscription 241 is refused whole; there is no
partial attachment and no waiting list.

## Monitoring

`corvid_channel_subscriptions` is a gauge per channel and
`corvid_subscribe_refused_total` counts rejections. A channel whose gauge sits
at the ceiling is one deploy away from refusing a subscriber that matters.
