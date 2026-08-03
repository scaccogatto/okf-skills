---
type: Decision
title: Auto-release on version bump
description: A push to main that changes plugin.json's version tags and publishes a GitHub release, so releasing can't be forgotten.
tags: [adr, ci, release]
status: stable
generated: { by: "agent:claude-opus-4-8", at: "2026-08-03T10:00:36Z" }
---

# Context

Releases were a manual `gh release create`, and it showed: versions 0.7.0 and
0.7.1 were bumped in `.claude-plugin/plugin.json` but never tagged or released,
so anyone pinned to a release tag never saw the dormant Stop hook that shipped in
them. A step a human has to remember is a step that eventually gets skipped.

# Decision

A [`release` workflow](/components/release-workflow.md)
(`.github/workflows/release.yml`) runs on every push to `main` that touches
`.claude-plugin/plugin.json`. It reads the version and, if no `okf--v<version>`
release exists yet, creates the tag and a GitHub release with auto-generated
notes. It is idempotent: a version already released is a no-op.

# Consequences

* Bumping the version in `plugin.json` is the single trigger; the release follows
  automatically, so it can no longer be forgotten.
* Notes are auto-generated from merged PRs since the last release; a curated
  title or body can still be edited on the release afterwards.
* The floating `v1` tag that `action.yml` is consumed as
  (`scaccogatto/okf-skills@v1`) is a separate major-version pointer, still moved
  by hand on purpose.
