---
type: Reference
title: Kestrel agent payload compression
description: Default payload compression on a Kestrel agent and what the setting costs on each side.
tags: [kestrel, agent, compression]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-15T09:00:00Z }
stale_after: 2026-08-01
---
# Kestrel agent payload compression

**Payload compression on a Kestrel agent is enabled by default.** An agent that
has never been configured compresses every payload above 4 KiB before it leaves
the host, and the collector decompresses transparently.

## Why the default is what it is

Agents were first deployed on links where egress was the scarce resource. With
compression on, a typical batch leaves the host at roughly a third of its
uncompressed size, at a cost of 3-6% of one core on the agent.

## What each setting does

| Setting | Agent CPU | Egress bytes |
|---|---|---|
| Compression on | +3-6% of a core | ~0.35x |
| Compression off | baseline | 1.0x |

The default therefore trades a small, predictable CPU cost on every host for a
large egress saving, which is the trade the fleet was sized for.

## Overriding it

`compression: false` in the agent block turns it off per host. The collector
accepts both shapes on the same port, so a fleet can be mixed during a rollout.
