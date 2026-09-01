---
type: Reference
title: Delivery filtering notes
description: Current filter precedence for Corvid message delivery.
tags: [corvid, filtering, delivery]
status: stable
generated: { by: human:okf-bench, at: 2026-07-24T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-24T09:00:00Z }
stale_after: 2027-08-31
---
# Delivery filtering notes

With per-cursor evaluation moved into the delivery path, the subscriber filter
decides: a subscriber rejecting a message does not receive it, whatever the
channel admits.

Channel filters remain as a cost control on fan-out.
