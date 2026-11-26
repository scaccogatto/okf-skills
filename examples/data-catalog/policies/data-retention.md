---
type: Policy
title: Sales data retention
description: How long Northwind Grocers keeps order data, and when it must be deleted or anonymized.
tags: [policy, retention, privacy, gdpr]
status: stable
generated: { by: "catalog-agent/1.2", at: "2026-10-15T09:00:00Z" }
stale_after: "2027-10-01"
sources:
  - id: retention-policy
    resource: https://example.com/northwind/legal/data-retention-policy-v3.pdf
    title: Data retention policy v3
    author: "team:legal"
    last_modified: "2026-07-01T00:00:00Z"
---

# Rule

| Data | Keep for | Then |
|------|----------|------|
| Order rows without `customer_id` | 10 years | Delete. |
| `customer_id` on order rows | 3 years after the last purchase | Set to null. |
| [Orders (legacy)](/tables/orders-legacy.md) export | Until 2027-11-19 | Drop the table. |

The ten-year period follows tax record rules, the three-year period follows the
loyalty programme terms.[^retention-policy] It applies to every table in the
[sales dataset](/datasets/sales.md).

[^retention-policy]: Data retention policy v3
