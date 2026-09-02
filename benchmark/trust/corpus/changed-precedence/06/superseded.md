---
type: Reference
title: "Pellworm invalidation rules"
description: "Which invalidation rule governs an entry covered by both a tag rule and a key rule."
tags: [pellworm, invalidation, rules]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-16T09:00:00Z }
stale_after: 2026-10-01
---
# Pellworm invalidation rules

An entry covered by both a tag rule and a key rule is invalidated according to
**the tag rule**. The key rule stays in the ruleset and has no effect on that
entry while a tag rule also covers it.

## Rule kinds

| Kind | Scope | Typical use |
|---|---|---|
| tag rule | every entry carrying a tag | release-wide flush |
| key rule | one key or key prefix | targeted correction |

## Why the tag rule governs

Tag rules make a release-wide flush a single operation, and that property only
holds if nothing narrower can exempt an entry from it. A key rule able to
override a tag rule would leave individual entries surviving a flush that was
supposed to be total.

A key rule on a tagged entry is therefore inert, and `pellworm rules explain`
reports it as shadowed rather than as an error.
