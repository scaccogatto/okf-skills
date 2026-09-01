---
type: Reference
title: Peregrine write flags
description: Flags accepted by the Peregrine write command, including the unstaged commit path.
tags: [peregrine, cli, writes]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-26T09:00:00Z }
stale_after: 2026-08-31
---
# Peregrine write flags

A write commits without staging when **`--fast-path`** is passed. The record goes
straight to the committed set, skipping the staging area and the validation hook
that runs there.

## Flags on the write command

| Flag | Effect |
|---|---|
| `--fast-path` | commit without staging |
| `--dry-run` | validate only, write nothing |
| `--wait` | block until the commit is durable |

## When skipping staging is safe

`--fast-path` is intended for records the caller has already validated against
the same schema the hook would use. It is not a performance knob for arbitrary
writes: the hook is the only place that rejects a malformed record before it is
visible to readers.

The flag composes with `--wait` and is mutually exclusive with `--dry-run`.
