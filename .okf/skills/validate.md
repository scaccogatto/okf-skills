---
type: Skill
title: validate skill
description: Deterministic §9 conformance check for an OKF bundle — not an eyeball pass.
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/validate/SKILL.md
tags: [skill, validation, ci]
timestamp: "2026-06-28T00:00:00Z"
---

# Overview

Runs the [validator script](/components/validator.md) against a bundle and
interprets the result: **ERROR** = a hard §9 failure (no parseable frontmatter, or
a missing/empty `type`); **warn** = soft guidance the spec tolerates.

# Usage

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" <bundle-dir> --strict
```

`${CLAUDE_SKILL_DIR}` resolves whether this runs as a plugin or a standalone
skills.sh skill — see the [self-contained-skills decision](/decisions/self-contained-skills.md).
The [okf skill](/skills/okf.md) calls this before declaring work done.
