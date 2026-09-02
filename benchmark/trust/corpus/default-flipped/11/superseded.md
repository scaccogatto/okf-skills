---
type: Reference
title: "Ashgrove workspace visibility"
description: "Visibility a new Ashgrove workspace is created with, and who can see it."
tags: [ashgrove, workspaces, visibility]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-03T09:00:00Z }
stale_after: 2026-09-25
---
# Ashgrove workspace visibility

A newly created Ashgrove workspace is visible to the whole **organisation**.
Anyone in the organisation can find it, open it read-only and request access to
write.

## Visibility levels

| Level | Who can find it | Who can read |
|---|---|---|
| private | members | members |
| organisation | everyone in the org | everyone in the org |
| public | anyone with the link | anyone with the link |

Organisation visibility is what makes work discoverable without a directory: a
colleague finds the workspace by searching rather than by being told it exists.

## Changing it

`ashgrove workspace visibility set` takes any level and applies immediately.
Lowering visibility does not revoke links already shared; those are revoked
separately.
