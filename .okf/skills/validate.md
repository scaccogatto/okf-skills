---
type: Skill
title: validate skill
description: Deterministic §11.1 conformance check for an OKF bundle — not an eyeball pass.
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/validate/SKILL.md
tags: [skill, validation, ci]
status: stable
generated: { by: "claude/opus-5.5", at: "2026-11-26T00:00:00Z" }
---

# Overview

Runs the [validator script](/components/validator.md) against a bundle and
interprets the result: **ERROR** = a hard §11.1 failure (frontmatter that does not parse as a
mapping, a duplicate key, or a broken root index); **warn** = soft guidance the spec tolerates, including a skipped non-concept `.md`
(no frontmatter or `type`) and a
v0.1 `timestamp` or `# Citations` section still awaiting migration.

# Usage

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" <bundle-dir> --strict
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" <bundle-dir> --migrate --strict
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" <bundle-dir> --strict --lint  # house style too
```

`--migrate` is the one non-read-only mode: it rewrites a v0.1 or v0.2 bundle to v0.3 in
place (see the [validator](/components/validator.md)), so the skill announces
what it will touch first. `--max-warnings N` sits between the permissive default
and `--strict`. `--lint` adds the okf-skills house-style warnings (missing
`title`, `description`, `tags`, `generated`), which are off by default.

`${CLAUDE_SKILL_DIR}` resolves whether this runs as a plugin or a standalone
skills.sh skill — see the [self-contained-skills decision](/decisions/self-contained-skills.md).
The [okf skill](/skills/okf.md) calls this before declaring work done.
