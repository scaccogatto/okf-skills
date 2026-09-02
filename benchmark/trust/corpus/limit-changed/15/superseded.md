---
type: Reference
title: "Marlowe topic tags"
description: "How many tags a Marlowe topic may carry and what tags are used for."
tags: [marlowe, topics, tags]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-29T09:00:00Z }
stale_after: 2026-08-18
---
# Marlowe topic tags

A single Marlowe topic may carry **256 tags**. An attempt to add the 257th fails
with `ML_TAG_LIMIT` and leaves the existing tags untouched.

## What tags are for

| Use | Typical tag count |
|---|---|
| Ownership and billing | 3-6 |
| Routing selectors | 10-40 |
| Generated provenance | up to 256 |

Generated provenance tags are the reason the ceiling is where it is: a pipeline
that stamps a tag per upstream stage reaches the hundreds on a wide topic.

## Tag semantics

Tags are unordered and unique per key; setting an existing key replaces its
value rather than adding a second tag.

## Monitoring

`marlowe_topic_tags` is a gauge per topic, and a topic near the ceiling usually
has a stage stamping unbounded values.
