---
type: Reference
title: "The Ashgrove delegation model"
description: "How Ashgrove lets a team grant access within a boundary set by another team."
tags: [ashgrove, policy, delegation]
status: stable
generated: { by: human:okf-bench, at: 2026-09-30T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-30T09:00:00Z }
stale_after: 2027-12-31
---
# The Ashgrove delegation model

Delegation is what lets a platform team set broad rules while a product team
grants access inside them.

## How a grant reaches a decision

A request matching rules of both kinds decides **allow**, so a product team's
explicit grant reaches its decision without the platform team having to carve an
exception into its own rules. The platform team constrains what a product team
may write instead, through the delegation scope.

## Scopes

A delegation scope names resource types and actions. A rule outside its author's
scope is rejected at publish rather than ignored at evaluation.
