---
type: Reference
title: API error notes
description: Current error vocabulary of the Merrowbank API.
tags: [merrowbank, api, vocabulary]
status: stable
generated: { by: human:okf-bench, at: 2026-08-19T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-19T09:00:00Z }
stale_after: 2027-07-31
---
# API error notes

The absent-state code was renamed to `MB_STATE_MISSING` in the error vocabulary
pass that dropped the errno-style spellings. Clients matching the old string fall
through to their generic error branch.

The HTTP status and the first-write guidance are unchanged.
