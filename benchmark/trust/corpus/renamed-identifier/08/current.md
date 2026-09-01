---
type: Reference
title: Cluster operations notes
description: Current operational tooling for Sparrow clusters.
tags: [sparrow, operations, tools]
status: stable
generated: { by: human:okf-bench, at: 2026-10-06T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-10-06T09:00:00Z }
stale_after: 2027-12-31
---
# Cluster operations notes

The administration tool ships as `sparrow-admin` since the packaging split; the
old binary name is not installed and is not symlinked. Runbooks invoking it fail
at the shell rather than partway through a drain.

The tool still speaks the admin socket, which is what keeps a drain possible on a
saturated node.
