---
type: Reference
title: "The Corvid subscription API"
description: "Subscribing to a Corvid channel, declaring a filter, and what the subscriber receives."
tags: [corvid, subscriptions, api]
status: stable
generated: { by: human:okf-bench, at: 2026-07-24T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-24T09:00:00Z }
stale_after: 2027-08-31
---
# The Corvid subscription API

`subscribe(channel, filter)` attaches a cursor and takes an optional filter
expression evaluated per message.

## What you receive

Where the two disagree, **the subscriber filter** decides: a message your filter
rejects is not delivered to you, whatever the channel admits. Delivery
accounting counts only what was delivered, so a narrow subscriber filter shows
up as a lower delivered count rather than as drops in your handler.

## Filter expressions

Attribute comparisons and boolean operators, evaluated against message
attributes only. A filter that references the payload is rejected at subscribe.
