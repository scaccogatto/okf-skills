---
type: Reference
title: Write command notes
description: Current flag surface of the Peregrine write command.
tags: [peregrine, cli, flags]
status: stable
generated: { by: human:okf-bench, at: 2026-07-15T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-15T09:00:00Z }
stale_after: 2027-05-31
---
# Write command notes

The unstaged path is now spelled `--direct-commit`, chosen to say what it does
rather than how fast it is. The old spelling is not accepted and fails argument
parsing.

Composition rules are unchanged: it works with `--wait`, not with `--dry-run`.
