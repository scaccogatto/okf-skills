---
type: Reference
title: "Personalising Thackery"
description: "Settings a Thackery user can adjust for themselves, and how they interact with shared ones."
tags: [thackery, settings, users]
status: stable
generated: { by: human:okf-bench, at: 2026-08-16T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-16T09:00:00Z }
stale_after: 2027-08-31
---
# Personalising Thackery

Editor, output verbosity, cache location and concurrency are all worth setting
per person rather than per workspace.

## Where they take effect

Where a workspace and a user both define a setting, the **user setting** applies,
so a personal concurrency limit survives working inside someone else's
workspace. `thackery config show --explain` prints where each effective value
came from.

## What not to personalise

Chunk size and ignore patterns change results rather than presentation; leave
those to the workspace even though you can set them.
