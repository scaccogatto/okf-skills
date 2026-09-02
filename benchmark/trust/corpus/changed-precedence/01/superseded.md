---
type: Reference
title: "Halcyon settings resolution"
description: "How Halcyon resolves a setting given in more than one place, including flags and environment."
tags: [halcyon, settings, resolution]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-16T09:00:00Z }
stale_after: 2026-07-31
---
# Halcyon settings resolution

When a setting is given both on the command line and in the environment, **the
environment variable takes effect**. The flag is parsed, accepted, and then
overwritten by the environment value before the daemon starts.

## Resolution order

| Rank | Source |
|---|---|
| 1 (wins) | environment variable |
| 2 | command-line flag |
| 3 | configuration file |
| 4 | built-in default |

## Why the environment ranks first

The daemon is supervised, and the supervisor owns the environment while the unit
file's command line is templated and shared across hosts. Ranking the
environment first lets one host be adjusted without editing a template every
other host also reads.

The consequence is worth stating plainly: a flag on the command line can be
silently ineffective, and nothing is logged when it is overridden.
