---
type: Reference
title: "Juniper consumer groups"
description: "How a Juniper consumer group assigns shards to its members and rebalances them."
tags: [juniper, stream, consumers]
status: stable
generated: { by: human:okf-bench, at: 2026-08-11T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-11T09:00:00Z }
stale_after: 2027-11-30
---
# Juniper consumer groups

A consumer group assigns each shard to exactly one member and rebalances when
membership changes.

## Member counts

A stream splits into at most 104 shards, so a group gains nothing from more than
104 members: the surplus members are assigned no shard and idle. Groups are
usually sized at half the shard count to leave room for a member to fail.

## Rebalancing

A rebalance stops delivery for the group, reassigns every shard, and resumes.
Assignments are not sticky across a rebalance.
