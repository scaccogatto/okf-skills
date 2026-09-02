---
type: Reference
title: "Osprey repository conventions"
description: "How an Osprey repository is organised: directories, naming and review ownership."
tags: [osprey, repository, conventions]
status: stable
generated: { by: human:okf-bench, at: 2026-08-08T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-08T09:00:00Z }
stale_after: 2027-07-31
---
# Osprey repository conventions

## Layout

Definitions are laid out per pipeline, following the recommended layout, one
file holding every job of a pipeline. Directories are per team, so ownership
rules name a directory and never a file.

## Review

Because a pipeline arrives as one file, a review sees the dependency edges in
the diff rather than having to reconstruct them across files, which is what
makes an ordering mistake catchable at review time.

## Naming

`<pipeline>.yaml`, lower case, no dates or version suffixes.
