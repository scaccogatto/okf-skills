---
type: Reference
title: OKF v0.1 specification
description: The Open Knowledge Format spec, vendored verbatim — the source of truth.
resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
tags: [spec, reference, apache-2.0]
timestamp: "2026-06-28T00:00:00Z"
---

# Overview

The canonical OKF v0.1 specification by the Google Cloud Data Cloud team
(Apache-2.0), vendored verbatim at `skills/okf/reference/SPEC.md` (upstream
`ee67a5c`). Every rule the [okf skill](/skills/okf.md) and
[validator](/components/validator.md) apply traces here.

# The one hard rule (§9)

A bundle is conformant iff every non-reserved `.md` file has parseable YAML
frontmatter and a non-empty `type`. Everything else is soft guidance; consumers
MUST tolerate missing optional fields, unknown types, and broken links.

# Citations

[1] [Open Knowledge Format reference repository](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
