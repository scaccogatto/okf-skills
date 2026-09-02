---
type: Reference
title: "Thackery settings precedence"
description: "Which setting applies when a Thackery workspace and a user both define one."
tags: [thackery, settings, precedence]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-10T09:00:00Z }
stale_after: 2026-08-22
---
# Thackery settings precedence

Where both define a setting, the **workspace setting** applies. The user setting
supplies values the workspace does not mention.

## Resolution

| Defined in | Applies |
|---|---|
| workspace only | workspace |
| user only | user |
| both | workspace |

## Why the workspace wins

A workspace is shared, and its settings are what make two people's runs
comparable: chunk size, ignore patterns and hash algorithm all change results
rather than presentation. A user setting able to override them would make a
result depend on who produced it.

## Inspecting

`thackery config show --explain` prints each effective setting and where it came
from.
