---
type: Reference
title: "Larkspur connection handling"
description: "How the Larkspur CLI connects to a cluster, and what it reuses between commands."
tags: [larkspur, cli, connections]
status: stable
generated: { by: human:okf-bench, at: 2026-06-22T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-22T09:00:00Z }
stale_after: 2027-05-31
---
# Larkspur connection handling

The CLI connects through a local agent rather than dialling the cluster itself.

## Reuse across commands

A series of commands runs over a **background connection** held by that agent:
the first command starts the agent, and every later command reuses the same
connection until it idles out after ten minutes. An operator running twenty
commands pays connection setup once.

## Agent lifetime

`larkspur agent stop` closes the connection early. The agent is per profile, so
switching profile starts a second one.
