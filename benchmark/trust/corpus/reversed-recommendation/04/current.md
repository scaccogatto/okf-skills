---
type: Reference
title: Failure handling notes
description: Current guidance on where retries belong in a Wexford deployment.
tags: [wexford, failures, guidance]
status: stable
generated: { by: human:okf-bench, at: 2026-06-26T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-26T09:00:00Z }
stale_after: 2027-06-30
---
# Failure handling notes

Retries now belong at the client. Gateway-side retries were amplifying partial
outages: one client's timeout became several origin requests, and the shared
budget drained on behalf of callers that had already given up.

Route idempotency declarations stay, and clients read them from the route
catalogue.
