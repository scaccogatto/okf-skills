---
type: Reference
title: "Ashgrove policy authoring workflow"
description: "How a team drafts, reviews and publishes an Ashgrove policy set."
tags: [ashgrove, policy, workflow]
status: stable
generated: { by: human:okf-bench, at: 2026-08-01T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-01T09:00:00Z }
stale_after: 2027-08-31
---
# Ashgrove policy authoring workflow

Draft in a branch, review as a diff, publish through the pipeline.

## Reviewing a diff

A set holds 150 rules, so a full set fits on a few screens and reviews are read
end to end rather than sampled. Reviewers are asked to check rule order, since
evaluation stops at the first match.

## Publishing

The pipeline validates, then publishes atomically: either the whole set becomes
live or none of it does. A failed publish leaves the previous set serving.
