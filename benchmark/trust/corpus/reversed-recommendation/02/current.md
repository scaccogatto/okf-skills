---
type: Reference
title: "The Selkie client library"
description: "What the Selkie client library does for you: connection handling, retries and write submission."
tags: [selkie, clients, library]
status: stable
generated: { by: human:okf-bench, at: 2026-08-21T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-21T09:00:00Z }
stale_after: 2027-08-31
---
# The Selkie client library

The library owns the connection, the retry policy and the submission path.

## Submitting writes

`client.write(record)` follows the recommended streamed shape: the record is
handed to the connection as it arrives and the server groups records into
commits. Applications do not need an accumulator of their own.

## Retries

The library retries transport failures with jitter and surfaces everything else.
Records carry keys, so a retried record is deduplicated server-side rather than
written twice.
