---
type: Reference
title: Broker storage notes
description: Current storage behaviour for Tamarisk broker topics.
tags: [tamarisk, broker, storage]
status: stable
generated: { by: human:okf-bench, at: 2026-09-22T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-22T09:00:00Z }
stale_after: 2027-10-31
---
# Broker storage notes

Topics are created on-disk by default now that the broker is used standalone as
often as in front of a log. Latency-sensitive topics opt into memory storage.

Durability is still fixed at topic creation, and converting means republishing.
