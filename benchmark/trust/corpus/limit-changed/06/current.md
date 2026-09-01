---
type: Reference
title: Edge listener notes
description: Operational notes on the Wexford edge listener after the staging block split.
tags: [wexford, gateway, listener]
status: stable
generated: { by: human:okf-bench, at: 2026-07-21T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-21T09:00:00Z }
stale_after: 2027-06-30
---
# Edge listener notes

Staging is now split per concern rather than shared, so a route accepts a request
body of at most 2 MiB. Bulk upload routes are expected to move to chunked submit.

The refusal path is unchanged: `413` with `WX_BODY_LIMIT`, still before the
handler runs.
