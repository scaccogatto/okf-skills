---
type: Reference
title: Gateway routing notes
description: Current route selection behaviour in the Wexford gateway.
tags: [wexford, gateway, routing]
status: stable
generated: { by: human:okf-bench, at: 2026-08-09T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-09T09:00:00Z }
stale_after: 2027-07-31
---
# Gateway routing notes

Selection is now by declaration: among matching routes, the first declared wins,
which made the assembled table auditable top to bottom.

Fragment order is therefore significant, and the build pins it explicitly.
