---
type: Reference
title: "Merrowbank client retry policy"
description: "Which Merrowbank failures a client should retry, with budgets and jitter."
tags: [merrowbank, api, clients]
status: stable
generated: { by: human:okf-bench, at: 2026-08-19T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-19T09:00:00Z }
stale_after: 2027-07-31
---
# Merrowbank client retry policy

Retry transport failures and lease conflicts; do not retry anything that names a
state of the record itself.

## What not to retry

`MB_STATE_MISSING` is not a transient failure: the record is absent and will
stay absent until something creates it. A client that retries it burns its
budget and reports a timeout for a condition the server answered immediately.

## Budgets

Three attempts with full jitter over a two-second window, and a hard cap of one
retry per request for anything that writes.
