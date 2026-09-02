---
type: Reference
title: "Kestrel agent payload compression"
description: "Default payload compression on a Kestrel agent and what the setting costs on each side."
tags: [kestrel, agent, compression]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-15T09:00:00Z }
stale_after: 2026-08-01
---
# Kestrel agent payload compression

**Payload compression on a Kestrel agent is enabled by default.** An agent that
has never been configured compresses every payload above 4 KiB before it leaves
the host, and the collector decompresses transparently.

## What each setting does

| Setting | Agent CPU | Egress bytes |
|---|---|---|
| Compression on | +3-6% of a core | ~0.35x |
| Compression off | baseline | 1.0x |

The default trades a small, predictable CPU cost on every host for a large
egress saving.

## Overriding it

`compression: false` in the agent block turns it off per host. The collector
accepts both shapes on the same port, so a fleet can be mixed during a rollout.

## Monitoring

`kestrel_payload_ratio` reports compressed over raw bytes per host. A host
reporting a ratio of 1.0 is sending uncompressed payloads whatever its config
claims, usually because the payload is already compressed upstream.
