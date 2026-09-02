---
type: Reference
title: "Halcyon change management"
description: "How a configuration change reaches a Halcyon fleet, from review to rollout."
tags: [halcyon, configuration, rollout]
status: stable
generated: { by: human:okf-bench, at: 2026-09-19T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-19T09:00:00Z }
stale_after: 2027-10-31
---
# Halcyon change management

A configuration change is reviewed, rendered per host, and rolled out one
failure domain at a time.

## Applying a change

The daemon picks up a changed file on **restart**, so the rollout step is a
drain-first restart per host. Drain-first makes the restart invisible to
clients, which is why the rollout does not need a separate connection-draining
stage.

## Rollback

Rollback is the previous rendered file plus the same restart, and the renders
are retained for 30 days so a rollback never re-renders from source.
