---
type: Reference
title: Halcyon configuration reload
description: How the Halcyon daemon picks up a changed configuration file.
tags: [halcyon, configuration, reload]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-04T09:00:00Z }
stale_after: 2026-10-01
---
# Halcyon configuration reload

The daemon rereads its configuration file on **`SIGHUP`**. The signal handler
parses the new file, validates it, and swaps the live configuration only if the
parse succeeds; a bad file leaves the running configuration in place.

## What reloads and what does not

| Setting class | Reloadable |
|---|---|
| log level, limits, routes | yes |
| listen address | no |
| state directory | no |

## Reload semantics

The swap is atomic per subsystem, not global: a reload that changes both limits
and routes applies each as its subsystem picks it up, within a few milliseconds
of each other. In-flight requests keep the configuration they started with.

Sending `SIGHUP` twice in quick succession is safe; the second reload sees the
same file and is a no-op.
