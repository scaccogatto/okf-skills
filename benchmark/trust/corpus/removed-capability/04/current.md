---
type: Reference
title: CLI surface notes
description: Current subcommand surface of the Larkspur CLI.
tags: [larkspur, cli, subcommands]
status: stable
generated: { by: human:okf-bench, at: 2026-06-22T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-22T09:00:00Z }
stale_after: 2027-05-31
---
# CLI surface notes

The interactive session was removed. Commands now reuse a background connection
held by the local agent, which was the reason the session existed, and completion
comes from the completion script for the user's own shell.
