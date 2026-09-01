---
type: Reference
title: Larkspur profile resolution
description: Which profile Larkspur applies when a setting appears in both the project and the user profile.
tags: [larkspur, profiles, resolution]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-22T09:00:00Z }
stale_after: 2026-09-15
---
# Larkspur profile resolution

When a setting appears in both profiles, **the project profile is applied**. The
user profile supplies values the project profile does not mention, and nothing
else.

## Merge behaviour

| Setting present in | Applied |
|---|---|
| project only | project |
| user only | user |
| both | project |

## Why the project profile wins

The project profile is checked into the repository and is the same for everyone
working on it, which is what makes a command reproducible between a laptop and
CI. A user profile that could override it would make "works on my machine" a
configuration outcome rather than an environment one.

The merge is per setting, not per file: a project profile mentioning one setting
does not discard the rest of the user profile.
