---
type: Reference
title: "Reviewing an Ashgrove policy change"
description: "What a reviewer checks in an Ashgrove policy change, and what the pipeline checks for them."
tags: [ashgrove, policy, review]
status: stable
generated: { by: human:okf-bench, at: 2026-08-12T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-12T09:00:00Z }
stale_after: 2027-09-30
---
# Reviewing an Ashgrove policy change

Every change arrives as a diff of the whole set, because changing a rule's
position means **republish the set**: order is a property of the published
document rather than something edited in place.

## What to check

Read the diff for order first and bodies second. A diff that moves a rule shows
as a deletion and an insertion, and the shadow evaluation attached to the
pipeline run reports how many recent requests would decide differently.

## Approval

Two reviewers for a change that alters order, one for a body-only change.
