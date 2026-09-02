---
type: Reference
title: "Cobble schema evolution"
description: "Evolving an event schema in Cobble without breaking the producers already sending it."
tags: [cobble, schema, evolution]
status: stable
generated: { by: human:okf-bench, at: 2026-07-19T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-19T09:00:00Z }
stale_after: 2027-06-30
---
# Cobble schema evolution

Add fields, never repurpose them; removals wait until no producer sends the
field.

## During a rollout

Malformed events are quarantined without explicit configuration, so a producer
still sending the old shape keeps running and its events land in the quarantine
store rather than being lost. Drain the quarantine after the rollout: replaying
it through the new schema recovers the window.

## Verifying

`cobble schema diff` compares two versions and names the producers affected by
each change.
