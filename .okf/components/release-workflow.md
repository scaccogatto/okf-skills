---
type: Tool
title: release.yml
description: GitHub Actions workflow that tags and publishes a release when the plugin version bumps.
resource: https://github.com/scaccogatto/okf-skills/blob/main/.github/workflows/release.yml
tags: [ci, release, github-actions]
status: stable
generated: { by: "agent:claude-opus-5-5", at: "2026-10-13T00:00:00Z" }
---

# Overview

The workflow that makes releasing automatic instead of a remembered manual step
(see the [auto-release decision](/decisions/auto-release.md)).

# Trigger and behaviour

Runs on push to `main` filtered to `paths: ['.claude-plugin/plugin.json']`, so
only a version change wakes it. It then:

1. reads `version` from `.claude-plugin/plugin.json`;
2. checks whether a `okf--v<version>` release already exists (`gh release view`);
3. if not, creates it with `gh release create`, tagging the pushed commit. The
   body is the version's `CHANGELOG.md` section, extracted by
   `.github/scripts/changelog_notes.py` and passed as `--notes-file`, with
   `--generate-notes` appending the PR list and contributors after it. Until
   0.10.2 the body was the generated PR list alone, so the changelog prose CI
   requires never reached the release page. A version with no section fails
   the release instead of shipping without notes.

A second step then force-moves the floating `v1` tag onto the same commit.
`uses: scaccogatto/okf-skills@v1` is what the README shows and what the Actions
ecosystem reads as "the latest 1.x", but nothing moved it: it sat frozen on a
docs commit from 0.6.0 and served adopters a validator four versions old, one
that rejected the `upkeep` flag the README told them to add. The repo is
pre-1.0, so `v1` tracks the latest release rather than a major line, which the
README states beside the example.

A `release` concurrency group (never cancelled) keeps two back-to-back bumps
from racing on the `v1` tag.

Idempotent by construction: a version already released is a no-op, and moving a
tag to where it already points changes nothing, so re-runs and unrelated pushes
do nothing. Needs only `contents: write` and the built-in `GITHUB_TOKEN`; the
tag push reuses the credentials `actions/checkout` persists.
