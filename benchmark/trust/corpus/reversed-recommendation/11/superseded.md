---
type: Reference
title: "Ashgrove policy set structure guidance"
description: "Whether to keep policy in one set or split it, and what each choice costs."
tags: [ashgrove, policy, structure]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-10T09:00:00Z }
stale_after: 2026-09-28
---
# Ashgrove policy set structure guidance

**Recommended: one large set.** Keep a tenancy's rules in a single set rather
than splitting them by resource type.

## Why one set

Evaluation stops at the first matching rule, so a single ordered set has exactly
one answer and the order is visible in one file. Several sets are combined by
deny-overrides, which means the effective decision is a function of every set
and cannot be read off any one of them.

| Structure | Effective decision readable in | Publish atomicity |
|---|---|---|
| one set | one file | whole policy |
| several sets | all files together | per set |

## Review

A single set is reviewed as an ordered diff, and rule order is part of the
review.
