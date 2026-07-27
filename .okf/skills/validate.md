---
type: Skill
title: validate skill
description: Deterministic §11 conformance check for an OKF bundle — not an eyeball pass.
resource: https://github.com/scaccogatto/okf-skills/blob/main/skills/validate/SKILL.md
tags: [skill, validation, ci]
status: stable
generated: { by: human:scaccogatto, at: "2026-06-28T00:00:00Z" }
---

# Overview

Runs the [validator script](/components/validator.md) against a bundle and
interprets the result: **ERROR** = a hard §11 failure (no parseable frontmatter, or
a missing/empty `type`); **warn** = soft guidance the spec tolerates, including a
v0.1 `timestamp` or `# Citations` section still awaiting migration.

# Usage

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" <bundle-dir> --strict
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_validate.py" <bundle-dir> --migrate --strict
```

`--migrate` is the one non-read-only mode: it rewrites a v0.1 bundle to v0.2 in
place (see the [validator](/components/validator.md)), so the skill announces
what it will touch first. `--max-warnings N` sits between the permissive default
and `--strict`.

`${CLAUDE_SKILL_DIR}` resolves whether this runs as a plugin or a standalone
skills.sh skill — see the [self-contained-skills decision](/decisions/self-contained-skills.md).
The [okf skill](/skills/okf.md) calls this before declaring work done.
