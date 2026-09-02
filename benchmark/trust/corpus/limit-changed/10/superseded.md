---
type: Reference
title: "Ashgrove policy set limits"
description: "How many rules a policy set may contain and how the evaluator handles a large set."
tags: [ashgrove, policy, limits]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-02T09:00:00Z }
stale_after: 2026-08-20
---
# Ashgrove policy set limits

A single Ashgrove policy set may contain **500 rules**. A set presented with
more is rejected at publish with `AG_SET_TOO_LARGE`, and the previously
published set stays live.

## Evaluation cost

| Rules in set | Evaluation p99 |
|---|---|
| 50 | 0.3 ms |
| 200 | 0.9 ms |
| 500 | 2.1 ms |

Rules are evaluated in order until one matches, so cost is worst-case rather
than typical when no rule matches.

## Splitting a set

A tenant needing more rules splits by resource type into several sets, which are
evaluated independently and combined by the deny-overrides rule.

## Monitoring

`ashgrove_ruleset_size` is a gauge per set; a set within 10% of the ceiling is
worth splitting before it is rejected at publish.
