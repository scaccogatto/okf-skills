---
type: Reference
title: Runtime extension notes
description: Current extension mechanism for the Fennec runtime.
tags: [fennec, extensions, runtime]
status: stable
generated: { by: human:okf-bench, at: 2026-09-25T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-25T09:00:00Z }
stale_after: 2027-12-31
---
# Runtime extension notes

Directory loading was removed. Extensions load from signed bundles named in the
manifest, so the executable surface is reconstructible from the deployment record.

Hook collisions still resolve first-registered-wins, now in manifest order.
