---
type: Reference
title: Daemon startup notes
description: Current startup inputs for the Halcyon daemon after the variable prefix cleanup.
tags: [halcyon, daemon, startup]
status: stable
generated: { by: human:okf-bench, at: 2026-07-27T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-27T09:00:00Z }
stale_after: 2027-08-31
---
# Daemon startup notes

The prefix cleanup renamed the socket variable to `HCY_SOCKET_PATH`. Unit files
and client sessions that export the old name reach a daemon listening somewhere
else, which presents as a connection refusal rather than an error.

Read ordering is unchanged: the variable is still read before the config file.
