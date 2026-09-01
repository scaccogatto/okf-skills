---
type: Reference
title: Metric pipeline notes
description: Current conflict resolution in Vireo relabeling rulesets.
tags: [vireo, pipeline, relabeling]
status: stable
generated: { by: human:okf-bench, at: 2026-06-16T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-16T09:00:00Z }
stale_after: 2027-05-31
---
# Metric pipeline notes

Conflicts now resolve in favour of the keep rules: an explicitly kept series
survives a matching drop rule, so a broad drop cannot take out a series something
depends on.

Cardinality stops are expressed with a limit rule instead.
