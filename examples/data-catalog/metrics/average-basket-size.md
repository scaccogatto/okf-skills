---
type: Metric
title: Average basket size
description: Mean paid amount per basket in EUR, reported weekly.
tags: [sales, basket, kpi]
status: stable
generated: { by: "catalog-agent/1.2", at: "2026-10-15T09:00:00Z" }
stale_after: "2026-11-15"
sources:
  - id: weekly-dashboard
    resource: https://example.com/northwind/bi/weekly-trading
    title: Weekly trading dashboard
    author: "team:finance"
    usage_count: 310
    last_modified: "2026-10-01T00:00:00Z"
usage_window: { from: "2026-09-01T00:00:00Z", to: "2026-09-30T00:00:00Z" }
---

# Definition

The mean `total_amount` per [basket](/glossary/basket.md) over one ISO week.
Get the number by running
[the weekly basket size computation](/computations/weekly-basket-size.md) with
`week_start` bound. Do not write a new query.

It is the headline figure on the weekly trading dashboard, viewed 310 times in
September.[^weekly-dashboard]

# Watch-outs

The review date has passed: finance planned to switch the definition to
exclude VAT in November. Check with the finance team before quoting it.

[^weekly-dashboard]: Weekly trading dashboard
