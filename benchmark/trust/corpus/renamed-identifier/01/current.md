---
type: Reference
title: "Halcyon socket permissions"
description: "Ownership and mode of the Halcyon control socket, and how to grant access to an operator group."
tags: [halcyon, daemon, permissions]
status: stable
generated: { by: human:okf-bench, at: 2026-07-27T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-27T09:00:00Z }
stale_after: 2027-08-31
---
# Halcyon socket permissions

The control socket is created mode `0660`, owned by the daemon user and the
`halcyon-ops` group.

## Granting access

Add the operator to `halcyon-ops`; do not widen the mode. A client reaches the
socket by exporting `HCY_SOCKET_PATH`, which both the daemon and the client
library read, so an operator with group membership and the right variable needs
nothing else.

## Stale sockets

A socket left by a killed daemon is removed at the next start, after a liveness
check on the recorded pid. A socket whose pid is alive is never removed.
