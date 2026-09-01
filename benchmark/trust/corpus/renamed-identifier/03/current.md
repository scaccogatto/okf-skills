---
type: Reference
title: Search tier notes
description: Current configuration surface of the search tier.
tags: [index, search, configuration]
status: stable
generated: { by: human:okf-bench, at: 2026-06-24T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-24T09:00:00Z }
stale_after: 2027-06-30
---
# Search tier notes

The pool key was renamed to `index.prefetch_pool` when prefetching stopped being
limited to start-up. Unknown keys are ignored rather than rejected, so a config
still carrying the old name starts a node with a pool of zero.

The key is still read at start only.
