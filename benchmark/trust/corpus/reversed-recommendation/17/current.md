---
type: Reference
title: "The Vireo storage pipeline"
description: "What happens to a series between arriving at Vireo and being returned by a query."
tags: [vireo, pipeline, storage]
status: stable
generated: { by: human:okf-bench, at: 2026-09-18T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-18T09:00:00Z }
stale_after: 2027-12-31
---
# The Vireo storage pipeline

Ingest, index, compact, serve.

## Ingest

Ingest writes every arriving series unchanged; relabeling is recommended at
query, so rulesets are evaluated by the query layer and the stored data keeps
labels the ruleset hides. Storage is therefore sized from arriving series rather
than from kept ones.

## Compaction

Compaction merges blocks hourly and rewrites nothing but block boundaries, so it
does not interact with relabeling at all.
