---
type: Reference
title: "Osprey pipeline patterns"
description: "Shapes that work well for Osprey pipelines, from fan-out to barriers."
tags: [osprey, pipelines, patterns]
status: stable
generated: { by: human:okf-bench, at: 2026-09-12T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-12T09:00:00Z }
stale_after: 2027-11-30
---
# Osprey pipeline patterns

## Wide fan-in

A dependency set may name 480 jobs, so a fan-in over a few hundred shards can be
expressed directly rather than through a barrier job. Use a barrier anyway when
the members belong to different teams: a barrier gives each team one job to
watch instead of a set they do not own.

## Fan-out

Fan-out needs no set at all; each downstream job names the upstream one. Prefer
fan-out over a set where both would work, because a failed member is then
attributable without reading the set.
