---
type: Reference
title: Larkspur CLI output formatting
description: Format the Larkspur CLI prints by default and how the format is selected.
tags: [larkspur, cli, output]
status: deprecated
generated: { by: human:okf-bench, at: 2026-01-11T09:00:00Z }
stale_after: 2026-06-15
---
# Larkspur CLI output formatting

The Larkspur CLI prints **table output by default**. Every list command renders
aligned columns with a header row, sized to the terminal width when one is
attached and to 100 columns when output is redirected.

## Why table was the default

The CLI was written for interactive use first: a human reading `larkspur jobs
list` wants columns, and the redirect case was expected to pass `--format`
explicitly anyway.

| Format | Header row | Stable across versions |
|---|---|---|
| table | yes | no, columns may change |
| ndjson | n/a | yes, keys are additive |

Scripts should not parse table output: columns are presentation, and they change
between releases without a compatibility note.

## Selecting a format

`--format` takes `table` or `ndjson` on every command, and `LARKSPUR_FORMAT` sets
it for a whole session.
