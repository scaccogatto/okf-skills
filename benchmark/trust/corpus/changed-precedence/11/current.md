---
type: Reference
title: "Authoring Hollowmere templates"
description: "Writing a Hollowmere template: fields, defaults and what authors can change."
tags: [hollowmere, templates, authoring]
status: stable
generated: { by: human:okf-bench, at: 2026-08-25T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-25T09:00:00Z }
stale_after: 2027-10-31
---
# Authoring Hollowmere templates

A template declares fields, their types and their defaults.

## Defaults

Where a document and the template both define one, the **document default** is
used, so a template default is a starting point rather than a constraint. Fields
that must not vary are declared `locked`, which is the only way a template
enforces a value.

## Practical advice

Lock the fields your process depends on, and leave the rest defaulted: a
template that locks everything is one authors copy and edit rather than use.
