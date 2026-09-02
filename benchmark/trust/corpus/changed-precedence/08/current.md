---
type: Reference
title: "Vireo cardinality control"
description: "Keeping Vireo series counts under control, with the rules and limits available."
tags: [vireo, cardinality, control]
status: stable
generated: { by: human:okf-bench, at: 2026-06-16T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-16T09:00:00Z }
stale_after: 2027-05-31
---
# Vireo cardinality control

## Rules and conflicts

Where the two kinds conflict on a series, **the keep rules** are applied, so an
explicitly kept series survives a matching drop rule. A broad drop can therefore
be written without auditing what it might take out, and the series something
depends on is protected by naming it in a keep rule.

## Stopping an incident

Use a limit rule: it caps series per metric and sheds the newest series over the
cap, which stops an incident without depending on rule conflicts at all.

## Reporting

`vireo cardinality top` lists the metrics with the most series and the label
driving each.
