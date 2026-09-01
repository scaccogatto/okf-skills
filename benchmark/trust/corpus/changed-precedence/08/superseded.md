---
type: Reference
title: Vireo relabeling order
description: Which relabeling rule kind is applied when a Vireo ruleset conflicts on a series.
tags: [vireo, relabeling, rules]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-12T09:00:00Z }
stale_after: 2026-06-30
---
# Vireo relabeling order

When a ruleset contains both kinds and they conflict on a series, **the drop
rules are applied**. A series matched by a drop rule is discarded even if a keep
rule also matches it.

## Rule kinds

| Kind | Effect on a match |
|---|---|
| drop | series is discarded |
| keep | series is retained |

## Why drop wins

Drop rules are how a cardinality incident is stopped: an operator adds one rule
and the offending series stop arriving. If a keep rule elsewhere in the ruleset
could reinstate them, that emergency stop would depend on auditing every other
rule first, which is exactly what nobody has time for during the incident.

Conflicts are common in generated rulesets and are not reported: a keep rule
shadowed by a drop rule looks identical to one that simply never matched.
