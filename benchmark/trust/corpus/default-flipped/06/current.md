---
type: Reference
title: CLI usage notes
description: Current behaviour of the Larkspur CLI in scripts and terminals.
tags: [larkspur, cli, usage]
status: stable
generated: { by: human:okf-bench, at: 2026-05-28T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-05-28T09:00:00Z }
stale_after: 2027-04-30
---
# CLI usage notes

Commands now emit ndjson by default, which makes piping the common case and
removes the parse-the-table trap. Interactive users pass `--format table`.

`--format` and `LARKSPUR_FORMAT` are unchanged.
