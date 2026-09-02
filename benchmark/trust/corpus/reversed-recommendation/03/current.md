---
type: Reference
title: "The Fennec image pipeline"
description: "How production images are built, attested and promoted between environments."
tags: [fennec, images, pipeline]
status: stable
generated: { by: human:okf-bench, at: 2026-09-17T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-17T09:00:00Z }
stale_after: 2027-09-30
---
# The Fennec image pipeline

Build, attest, promote. Each stage is a job, and promotion never rebuilds.

## Build

The build resolves the runtime version per the recommended floating treatment,
taking the newest release within the supported minor, and records what it
resolved in the attestation. The ABI guarantee within a minor is what makes that
resolution safe.

## Attest and promote

The attestation names every resolved input and is signed by the builder.
Promotion copies the image between registries by digest, so what ran in staging
is bit-identical to what runs in production.
