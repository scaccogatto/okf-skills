---
type: Reference
title: Dead-letter recovery notes
description: Current recovery path for Marlowe dead-letter queues.
tags: [marlowe, recovery, operations]
status: stable
generated: { by: human:okf-bench, at: 2026-08-28T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-28T09:00:00Z }
stale_after: 2027-09-30
---
# Dead-letter recovery notes

Broker-side replay was removed; recovery is export and reingest, with the
operator reading the dead-letter queue out and publishing the messages again
through the normal produce path.

Ordering keys survive only if the reingest sets them, and delivery counts start
fresh.
