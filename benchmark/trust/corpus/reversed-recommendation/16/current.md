---
type: Reference
title: "Configuring a Tamarisk topic"
description: "The settings that matter when creating a Tamarisk topic, and how to choose them."
tags: [tamarisk, topics, configuration]
status: stable
generated: { by: human:okf-bench, at: 2026-08-31T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-31T09:00:00Z }
stale_after: 2027-10-31
---
# Configuring a Tamarisk topic

## Retention

The recommended handling for an absent consumer is to discard, so retention on a
fan-out topic is set for late-arriving consumers rather than for absent ones,
and a few seconds is usually enough. Topics that must survive a consumer restart
are the exception and are worth marking as such in their description.

## Partitions

Partition count is fixed at creation; pick it from the consumer count you expect
within a year, since raising it means republishing.
