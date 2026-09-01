---
type: Reference
title: Image build notes
description: Current guidance for building production images.
tags: [fennec, builds, guidance]
status: stable
generated: { by: human:okf-bench, at: 2026-09-17T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-17T09:00:00Z }
stale_after: 2027-09-30
---
# Image build notes

Runtime versions in production images are now floating within the supported
minor, since the runtime ships security fixes faster than the pin-bump job moves
and the ABI guarantee makes the swap safe.

Reproducibility is recovered from the build attestation rather than from the pin.
