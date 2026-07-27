---
type: Reference
title: OKF v0.2 specification
description: The Open Knowledge Format spec, vendored verbatim — the source of truth.
resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
tags: [spec, reference, apache-2.0]
status: stable
generated: { by: human:scaccogatto, at: "2026-07-27T00:00:00Z" }
sources:
  - id: okf-upstream
    resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
    title: Open Knowledge Format reference repository
    author: team:google-cloud-data-cloud
    last_modified: 2026-07-27
---

# Overview

The canonical OKF v0.2 specification by the Google Cloud Data Cloud team
(Apache-2.0), vendored verbatim at `skills/okf/reference/SPEC.md` (upstream
`3fcbb9f`).[^okf-upstream] Every rule the [okf skill](/skills/okf.md) and
[validator](/components/validator.md) apply traces here.

# The one hard rule (§11)

A bundle is conformant iff every non-reserved `.md` file has parseable YAML
frontmatter and a non-empty `type`. Everything else is soft guidance; consumers
MUST tolerate missing optional fields, unknown types, and broken links.

# What v0.2 adds (§13)

| Family | Fields | Purpose |
|--------|--------|---------|
| Provenance | `sources[]` (`resource`, `id`, `author`, `usage_count`, `last_modified`), `usage_window` | Where a concept came from, with credibility signals. |
| Trust | `generated: {by, at}`, `verified[]` | Who wrote it, who confirmed it. |
| Lifecycle | `status`, `stale_after` | Is it current, is it still true. |
| Attestation | `type: Attested Computation` + `runtime`, `parameters`, `computation`, `executor`, `attester` | Was this number produced the sanctioned way. |

Two v0.1 constructs are superseded: `timestamp` (now `generated.at`) and the
body `# Citations` list (now `sources`). This toolkit still reads both — see the
[dual-read decision](/decisions/okf-v02-dual-read.md).

[^okf-upstream]: Open Knowledge Format reference repository
