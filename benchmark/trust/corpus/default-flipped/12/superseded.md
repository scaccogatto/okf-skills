---
type: Reference
title: "Cobble malformed event handling"
description: "What a Cobble collector does with an event that fails schema validation."
tags: [cobble, events, validation]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-23T09:00:00Z }
stale_after: 2026-07-25
---
# Cobble malformed event handling

A Cobble collector **rejects** a malformed event by default: the event is
refused, the producer is told which field failed, and nothing is stored.

## The options

| Handling | Producer learns | Event stored |
|---|---|---|
| reject | immediately, in the response | no |
| quarantine | from a report | yes, out of band |

Rejection puts the failure in front of the producer at the moment it happens,
which is what keeps a schema drift from being discovered a week later in a
dashboard.

## Configuring it

`validation.on_failure` takes either value per stream. The setting does not
affect batches: a batch with one malformed event fails whole under rejection.

## Monitoring

`cobble_validation_failures_total` counts by stream and field.
