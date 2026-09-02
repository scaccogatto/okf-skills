---
type: Reference
title: "Fennec plugin loading"
description: "Where the Fennec runtime loads plugins from and how they are discovered."
tags: [fennec, plugins, loading]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-11T09:00:00Z }
stale_after: 2026-10-15
---
# Fennec plugin loading

The Fennec runtime loads plugins from **a directory**: every shared object under
the configured plugin path is discovered at start and loaded in lexical order.

## Discovery rules

| Rule | Behaviour |
|---|---|
| Path | `plugins.path`, a single directory |
| Order | lexical by filename |
| Failure | one plugin failing aborts start |

## What directory loading costs

Dropping a file in a directory is the whole deployment step, which is why
sidecar-style extensions are built this way. The cost is that the runtime's
executable surface is whatever the filesystem holds at start, so the plugin set
is not visible in any manifest.

Load order matters when two plugins register the same hook: the first wins and
the second logs a warning.
