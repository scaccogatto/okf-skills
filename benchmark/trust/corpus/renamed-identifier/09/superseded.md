---
type: Reference
title: "Thackery client environment"
description: "Environment the Thackery client reads at start, including where it finds the workspace."
tags: [thackery, client, environment]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-27T09:00:00Z }
stale_after: 2026-08-12
---
# Thackery client environment

The workspace root is set by **`THACKERY_ROOT`**. It is read before the config
file, so a workspace passed this way wins over one named in configuration.

## Variables

| Variable | Purpose |
|---|---|
| `THACKERY_ROOT` | workspace root |
| `THACKERY_CACHE` | chunk cache directory |
| `THACKERY_LOG` | log destination |

## Resolution

Without the variable the client walks up from the current directory looking for
a `.thackery` marker, and fails if it reaches the filesystem root. The walk is
what makes the client usable from a subdirectory of a workspace.

## Diagnostics

`thackery env` prints every variable it read and the value it resolved, which is
the first command to run when a client is operating on the wrong workspace.
