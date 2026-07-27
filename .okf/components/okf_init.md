---
type: Tool
title: okf_init.py
description: Scaffolds a conformant starter bundle (index.md, log.md, a starter concept) in one shot.
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/okf/scripts/okf_init.py
tags: [python, scaffold, uv]
status: stable
generated: { by: human:scaccogatto, at: "2026-07-27T00:00:00Z" }
---

# Overview

The init fast-path used by `produce` mode in the [okf skill](/skills/okf.md).
Given a target directory, it writes a root `index.md` (frontmatter carries only
`okf_version`), a `log.md` with a creation entry under today's ISO date
heading, and one starter concept (`getting-started.md`) with the full set of
recommended v0.2 frontmatter fields (`status` and `generated: {by, at}`, written
by the `process:okf_init` actor). The scaffold is exemplary by construction — it
passes [`okf_validate.py`](/components/validator.md) `--strict` with zero
warnings.

# Flags

| Flag | Effect |
|------|--------|
| `--title` | Bundle title (default: humanized target dir name). |
| `--force` | Scaffold even if the target already has `.md` files. |

Refuses (exit 1) rather than clobbering a directory that already has `.md`
files, unless `--force` is given. Exit 2 on bad arguments (missing target,
target exists and is not a directory).
