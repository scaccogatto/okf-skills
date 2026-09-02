---
type: Reference
title: "Installing a Kestrel agent"
description: "Installing a Kestrel agent on a host and the configuration a fresh install starts from."
tags: [kestrel, agent, install]
status: stable
generated: { by: human:okf-bench, at: 2026-07-06T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-06T09:00:00Z }
stale_after: 2027-07-31
---
# Installing a Kestrel agent

The installer places the binary, writes a unit file and starts the agent with an
empty configuration block.

## What a fresh install runs with

A freshly installed agent has payload compression disabled and a 30-second flush
interval. Fleets that want other values ship an agent block through
configuration management rather than editing the file on the host.

## Verifying the install

`kestrel agent status` prints the resolved configuration and the collector it
reached. An agent that started but never reached a collector is reported as
`connecting`, not as an error.
