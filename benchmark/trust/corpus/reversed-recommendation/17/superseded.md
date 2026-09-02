---
type: Reference
title: "Vireo relabeling placement guidance"
description: "Where a relabeling ruleset should be applied, and what each placement costs."
tags: [vireo, relabeling, guidance]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-12T09:00:00Z }
stale_after: 2026-10-06
---
# Vireo relabeling placement guidance

**Recommended: at ingest.** A relabeling ruleset should run as series arrive, so
what is stored is already what you meant to store.

## The comparison

| Placement | Storage cost | Reversible |
|---|---|---|
| at ingest | only kept series stored | no, dropped series are gone |
| at query | every series stored | yes |

Ingest-time relabeling is what makes a cardinality rule actually save money: a
rule applied at query still pays to store everything it hides.

## Rollout

Apply a new ruleset to a single ingester first and compare its accepted series
count against its peers before rolling out; a rule that drops more than intended
is unrecoverable for the window it ran.
