---
type: Reference
title: Profile notes
description: Current profile merge behaviour in Larkspur.
tags: [larkspur, profiles, merge]
status: stable
generated: { by: human:okf-bench, at: 2026-08-23T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-23T09:00:00Z }
stale_after: 2027-12-31
---
# Profile notes

The merge now applies the user profile where both mention a setting, so an
operator's own credentials and output preferences are not overwritten by a
checked-in file.

Reproducibility between a laptop and CI comes from `--profile` instead.
