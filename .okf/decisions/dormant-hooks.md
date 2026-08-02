---
type: Decision
title: Ship a dormant Stop hook — opt-in enforced upkeep
description: Supersede zero-hooks with a Stop hook that is a no-op unless the bundle opts in.
tags: [adr, ux, trust]
status: stable
generated: { by: "agent:claude-fable-5", at: "2026-08-02T11:39:43Z" }
---

# Context

Soft-mode upkeep ([no hooks](/decisions/no-hooks.md)) depends entirely on a
project's `CLAUDE.md` carrying the pasted snippet — nothing enforces it, and
adoption is invisible to the plugin. Users have asked for upkeep enforcement
that ships *with* the plugin rather than living outside it. The concerns
behind zero hooks are still valid for an always-ON hook: observing every
session is intrusive, and it risks failing third-party marketplace safety
review.

# Decision

Ship one `Stop` hook, **dormant by default**: `hooks/okf-stop-check.sh` reads
one file and exits unless *both* hold —

1. the target repo's bundle opts in with `upkeep: enforced` in
   `.okf/index.md` frontmatter, and
2. the user has not opted out with `OKF_HOOK=off` in their environment.

Enforcement is therefore a per-bundle, versioned declaration — checked into
the repo the bundle lives in — not a plugin-wide default. The
[CLAUDE.md snippet](/decisions/no-hooks.md) remains the soft-mode path for
bundles that never set `upkeep: enforced`.

# Consequences

* Passes the same safety review the [no-hooks decision](/decisions/no-hooks.md)
  was written to pass: without the opt-in frontmatter, the hook is a single
  file read and an exit, on every session, for every repo that doesn't ask for
  it.
* Enforcement becomes distributable with the plugin instead of copy-pasted
  per project — see the [stop-hook component](/components/stop-hook.md).
* [Ship no hooks](/decisions/no-hooks.md) is superseded by this decision.
