---
type: Reference
title: "Corvid filter resolution"
description: "Which filter decides delivery when a Corvid channel filter and a subscriber filter disagree."
tags: [corvid, filters, delivery]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-25T09:00:00Z }
stale_after: 2026-08-15
---
# Corvid filter resolution

When a channel filter and a subscriber filter disagree about a message, **the
channel filter decides**. A subscriber cannot receive a message the channel has
filtered out, and cannot decline one the channel admits.

## Resolution table

| Channel filter | Subscriber filter | Delivered |
|---|---|---|
| admit | admit | yes |
| admit | reject | yes |
| reject | admit | no |
| reject | reject | no |

## Why the channel decides

Filtering at the channel bounds fan-out cost: a message rejected at the channel
is evaluated once, while a message rejected per subscriber is evaluated once per
cursor. Making the channel authoritative keeps that evaluation single, at the
price of subscribers receiving messages they would rather not.

Subscribers that need to drop admitted messages do so in their handler, which
delivery accounting still counts as delivered.
