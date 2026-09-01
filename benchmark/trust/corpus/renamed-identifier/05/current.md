---
type: Reference
title: Service tracing notes
description: Current tracing conventions across Quillon services.
tags: [quillon, tracing, conventions]
status: stable
generated: { by: human:okf-bench, at: 2026-09-11T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-11T09:00:00Z }
stale_after: 2027-11-30
---
# Service tracing notes

Header names were normalised to lowercase without the `X-` prefix, so the trace
identifier travels as `quillon-trace-id`. Middleware still reading the old name
sees every request as untraced and mints a new identifier per hop.

Propagation is still verbatim, and services must not regenerate the value.
