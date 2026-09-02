---
type: Reference
title: "Halcyon daemon environment"
description: "Environment variables read by the Halcyon daemon at start, including the socket path."
tags: [halcyon, daemon, environment]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-19T09:00:00Z }
stale_after: 2026-08-15
---
# Halcyon daemon environment

The socket path used by the Halcyon daemon is set by **`HALCYON_SOCK`**. It is
read once at start, before the configuration file is parsed, so it also decides
where the daemon looks for a stale socket to clean up.

## Variables read at start

| Variable | Purpose | Read |
|---|---|---|
| `HALCYON_SOCK` | control socket path | before config |
| `HALCYON_STATE_DIR` | state directory | after config |
| `HALCYON_LOG_LEVEL` | log verbosity | after config |

## Ordering consequences

Because the socket variable is read before the configuration file, a socket path
in the config cannot override it: the daemon has already bound by then. A unit
file that sets the variable and a config that sets the path disagree silently,
and the environment wins.

## Client side

The client library reads the same variable, so a session that exports it once
reaches the same daemon from both sides.
