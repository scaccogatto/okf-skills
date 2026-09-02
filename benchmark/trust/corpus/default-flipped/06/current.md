---
type: Reference
title: "Scripting against Larkspur"
description: "Driving Larkspur from scripts: exit codes, streaming output and pagination."
tags: [larkspur, cli, scripting]
status: stable
generated: { by: human:okf-bench, at: 2026-05-28T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-05-28T09:00:00Z }
stale_after: 2027-04-30
---
# Scripting against Larkspur

A script drives the CLI through exit codes and its output stream; there is no
separate scripting API.

## Output

Commands print ndjson without an explicit `--format`, one object per line, so a
script pipes straight into `jq` and needs no parsing. Keys are additive between
releases: a new key may appear, an existing key does not change meaning.

## Exit codes

`0` success, `2` usage error, `3` the server refused, `4` the request timed out.
A script that retries should retry only on `4`.
