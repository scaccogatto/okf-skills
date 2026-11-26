---
type: Reference
title: OKF v0.3 specification
description: The Open Knowledge Format spec, vendored verbatim — the source of truth.
resource: https://github.com/open-knowledge-format/open-knowledge-format
tags: [spec, reference, apache-2.0]
status: stable
generated: { by: "human:scaccogatto", at: "2026-11-26T00:00:00Z" }
sources:
  - id: okf-upstream
    resource: https://github.com/open-knowledge-format/open-knowledge-format
    title: Open Knowledge Format reference repository
    author: "team:open-knowledge-format"
    last_modified: "2026-11-18T17:00:25Z"
---

# Overview

The canonical OKF v0.3 specification (Apache-2.0, (c) Google LLC), vendored
verbatim at `skills/okf/reference/SPEC.md` (upstream `527e81a`).[^okf-upstream]
Every rule the [okf skill](../skills/okf.md) and
[validator](../components/validator.md) apply traces here.

# The hard rules (§11.1)

A bundle is conformant when every frontmatter block in a `.md` file parses as a
YAML mapping, and the reserved files (`index.md`, `log.md`) follow §8 and §9. A
`.md` file without frontmatter or without `type` is not a concept (§3.2): it is
skipped, which is how `README.md` or `SKILL.md` can live inside a bundle.
Everything else is soft guidance. Consumers MUST tolerate missing optional
fields, unknown types, unknown keys and broken links.

# The families (§5, §10)

| Family | Fields | Purpose |
|--------|--------|---------|
| Provenance | `sources[]` (`resource`, `id`, `author`, `usage_count`, `last_modified`), `usage_window` | Where a concept came from, with credibility signals. |
| Trust | `generated: {by, at}`, `verified[]` (`by` and `at` both required) | Who wrote it, who confirmed it. The tier counts only events at or after `generated.at`. |
| Lifecycle | `status`, `superseded_by`, `stale_after` | Is it current, what replaced it, when to check again. |
| Attestation | `type: Attested Computation` + `runtime`, `parameters`, `computation`, `executor`, `attester` | Was this number produced the sanctioned way. |

Bundle metadata lives in the root `index.md` frontmatter: `okf_version`,
`title`, `description`, `license` (§8.1). Extension keys are allowed anywhere,
and the `x-` prefix is reserved for them (§4.1).

# What v0.3 changed (§13)

- **Breaking:** a path field without a leading `/` resolves from its file's
  directory. Bundles declaring 0.2 or none may fall back to the root (§12.1).
- **Breaking:** trust tiers count only current verification events (§5.3).
- Timestamps: a date-only value is valid (start of day UTC). A date-time
  without an offset is invalid (§5).
- An unknown `status` is not `stable` (§5.4). An unparseable `stale_after` is
  never fresh (§5.5).

The v0.1 constructs (`timestamp`, body `# Citations`) are still read, now
described in Appendix B. See the [dual-read decision](../decisions/okf-v02-dual-read.md).

## History

- 2026-09-21: upstream moved to GoogleCloudPlatform/open-knowledge-format (the
  knowledge-catalog copy is frozen). The three date fields (stale_after,
  sources[].last_modified, usage_window) became ISO 8601 datetimes, re-vendored
  at 0b87c52.
- 2026-11-26: upstream moved to open-knowledge-format/open-knowledge-format
  (the GoogleCloudPlatform copy is deprecated) and released v0.3, re-vendored at
  527e81a.

[^okf-upstream]: Open Knowledge Format reference repository
