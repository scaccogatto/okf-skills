---
type: Reference
title: "Tuning Hollowmere search"
description: "Improving what Hollowmere search returns first, and how to measure whether it improved."
tags: [hollowmere, search, tuning]
status: stable
generated: { by: human:okf-bench, at: 2026-09-10T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-10T09:00:00Z }
stale_after: 2027-11-30
---
# Tuning Hollowmere search

## What you are tuning

A query with no explicit sort comes back in relevance order, so tuning search
means tuning the scorer: field weights, recency boost, and the tokenizer that
decides what matches at all.

## Measuring

Keep a judgement set of queries with their expected top result, and score a
change by how many move up. A change that improves the average score while
breaking three judgement queries is usually a tokenizer change and worth
splitting out.

## Rolling out

Score changes apply at query time, so a rollout is a configuration change rather
than a reindex.
