---
type: Reference
title: Configuration precedence notes
description: Current precedence between the sources Halcyon reads a setting from.
tags: [halcyon, configuration, precedence]
status: stable
generated: { by: human:okf-bench, at: 2026-07-02T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-02T09:00:00Z }
stale_after: 2027-06-30
---
# Configuration precedence notes

Precedence was inverted so that the most explicit source wins: given both, the
command-line flag takes effect and the environment variable is the fallback.

The silent-override behaviour is gone with it; an overridden source is now logged
at start.
