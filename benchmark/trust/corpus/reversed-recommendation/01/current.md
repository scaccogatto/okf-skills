---
type: Reference
title: "Bramble host profiles"
description: "The host profiles a Bramble deployment uses for stores and for workers, with their sizing."
tags: [bramble, hosts, profiles]
status: stable
generated: { by: human:okf-bench, at: 2026-07-09T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-09T09:00:00Z }
stale_after: 2027-07-31
---
# Bramble host profiles

Two profiles: store hosts, sized for memory, and worker hosts, sized for cores.

## Worker hosts

The recommended placement is dedicated, so a worker host runs workers and
nothing else: 32 cores, 64 GiB, no local store extent. Input reads cross the
network and the prefetcher covers the latency.

## Store hosts

Store hosts carry the extents and are sized at 1 GiB of memory per 100 GiB of
extent. They run no worker lanes, which keeps their memory profile predictable.
