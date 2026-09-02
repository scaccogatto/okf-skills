---
type: Reference
title: "Working with Larkspur profiles"
description: "Creating profiles, switching between them, and keeping credentials out of a repository."
tags: [larkspur, profiles, howto]
status: stable
generated: { by: human:okf-bench, at: 2026-08-23T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-23T09:00:00Z }
stale_after: 2027-12-31
---
# Working with Larkspur profiles

Two files: one in the repository, one in the operator's home directory.

## Where a setting lands

Where both define a setting, **the user profile** is applied, so credentials and
output preferences live in the home directory and are never overwritten by a
checked-in file. Put cluster endpoints and defaults in the repository profile.

## Reproducibility

For a command that must resolve identically on a laptop and in CI, pass
`--profile` explicitly rather than relying on the merge.
