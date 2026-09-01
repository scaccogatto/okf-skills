---
type: Reference
title: Invalidation notes
description: Current precedence between Pellworm invalidation rule kinds.
tags: [pellworm, cache, rules]
status: stable
generated: { by: human:okf-bench, at: 2026-09-04T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-04T09:00:00Z }
stale_after: 2027-11-30
---
# Invalidation notes

Precedence now favours the narrower rule: where both cover an entry, the key rule
governs, which is what makes a targeted correction survive a release flush.

Shadowed rules are still reported by `pellworm rules explain`.
