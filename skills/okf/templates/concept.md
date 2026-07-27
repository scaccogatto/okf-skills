---
type: <Concept type, e.g. Service, BigQuery Table, Metric, Playbook, Decision>
title: <Human-readable display name>
description: <Single sentence summarizing the concept.>
resource: <Canonical URI of the underlying asset — omit for abstract concepts>
tags: [<tag>, <tag>]
status: stable                    # draft | stable | deprecated; absent means stable
generated: { by: <actor>, at: <ISO 8601, e.g. 2026-06-14T10:00:00Z> }
verified: { by: human:<id>, at: <ISO 8601> }   # omit until someone confirms it
stale_after: <YYYY-MM-DD>         # omit when the content does not expire
sources:                          # what this was derived from; omit if nothing
  - id: <short-key>
    resource: <URL, bundle path, or scope descriptor>
    title: <Human-readable label>
    author: <actor>               # optional credibility signal
    last_modified: <YYYY-MM-DD>   # when the source itself last changed
---

<!--
  Actors (§7): `<producer>/<version>` for an agent, `human:<id>` for a person,
  `process:<id>` for an automated job. Use `human:` whenever a person authored
  or signed off — consumers key trust tiers off that prefix.
-->

# Overview

<What this concept is and why it matters. Attribute a sourced claim with a
footnote whose label is a `sources[].id`.[^short-key]>

# Schema

<Use for assets with fields/columns; otherwise replace with relevant sections.>

| Field | Type | Description |
|-------|------|-------------|
|       |      |             |

[^short-key]: <Human-readable label of the source>
