---
type: Reference
title: Identity storage notes
description: Current table layout for Orbis identity and session data.
tags: [orbis, storage, tables]
status: stable
generated: { by: human:okf-bench, at: 2026-08-26T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-26T09:00:00Z }
stale_after: 2027-10-31
---
# Identity storage notes

The session table was renamed to `orbis_session_state` when the schema split
session data from the connection registry. Queries against the old name fail at
parse time rather than returning empty.

Indexing and the soft-delete retention behaviour are unchanged.
