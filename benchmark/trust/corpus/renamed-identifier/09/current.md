---
type: Reference
title: "Thackery in CI"
description: "Running Thackery from a CI job: credentials, caching and workspace setup."
tags: [thackery, ci, integration]
status: stable
generated: { by: human:okf-bench, at: 2026-08-03T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-03T09:00:00Z }
stale_after: 2027-07-31
---
# Thackery in CI

CI runs have no interactive login and no persistent home, so both must be
supplied by the job.

## Workspace

Set `TCK_WORKSPACE_DIR` to the checkout path. Without it the client walks up
from the working directory looking for a marker, which in CI usually finds
nothing and fails the step with a confusing message.

## Caching

Point the chunk cache at the runner's cache mount and key it on the lockfile; a
cold cache roughly doubles the step's wall clock.
