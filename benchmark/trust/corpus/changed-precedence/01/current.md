---
type: Reference
title: "Halcyon deployment topologies"
description: "How Halcyon is deployed under a supervisor, in a container, and in a developer shell."
tags: [halcyon, deployment, topologies]
status: stable
generated: { by: human:okf-bench, at: 2026-07-02T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-02T09:00:00Z }
stale_after: 2027-06-30
---
# Halcyon deployment topologies

## Under a supervisor

The unit file sets the environment and a templated command line. Where both give
a setting, the **command-line flag** takes effect, so per-host overrides go in
the flags and the environment carries the fleet-wide baseline.

## In a container

The image entrypoint is the same command line; the orchestrator supplies the
environment. Overridden sources are logged at start, which is how a
misconfigured deployment is spotted without a shell on the host.

## In a developer shell

Run the binary directly with flags; no configuration file is required.
