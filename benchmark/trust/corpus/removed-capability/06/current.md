---
type: Reference
title: "Packaging a Fennec extension"
description: "Building, signing and shipping a Fennec extension so a runtime will load it."
tags: [fennec, extensions, packaging]
status: stable
generated: { by: human:okf-bench, at: 2026-09-25T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-25T09:00:00Z }
stale_after: 2027-12-31
---
# Packaging a Fennec extension

An extension ships as a bundle: the compiled object, a manifest and a signature.

## What the runtime accepts

The runtime loads plugins from **signed bundles** named in its manifest, so a
bundle that is unsigned, signed by an untrusted key, or absent from the manifest
is not loaded and the runtime says so at start.

## Signing

Sign with the team key registered in the extension registry. Key rotation
requires re-signing existing bundles; the runtime does not accept a signature
from a retired key.
