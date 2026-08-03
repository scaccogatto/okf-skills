---
type: Tool
title: release.yml
description: GitHub Actions workflow that tags and publishes a release when the plugin version bumps.
resource: https://github.com/scaccogatto/okf-skills/blob/main/.github/workflows/release.yml
tags: [ci, release, github-actions]
status: stable
generated: { by: "agent:claude-opus-4-8", at: "2026-08-03T10:00:36Z" }
---

# Overview

The workflow that makes releasing automatic instead of a remembered manual step
(see the [auto-release decision](/decisions/auto-release.md)).

# Trigger and behaviour

Runs on push to `main` filtered to `paths: ['.claude-plugin/plugin.json']`, so
only a version change wakes it. It then:

1. reads `version` from `.claude-plugin/plugin.json`;
2. checks whether a `okf--v<version>` release already exists (`gh release view`);
3. if not, creates it with `gh release create --generate-notes`, tagging the
   pushed commit.

Idempotent by construction: a version already released is a no-op, so re-runs and
unrelated pushes do nothing. Needs only `contents: write` and the built-in
`GITHUB_TOKEN`.
