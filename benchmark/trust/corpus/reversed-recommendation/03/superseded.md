---
type: Reference
title: Fennec runtime version guidance for images
description: How production images should treat the Fennec runtime version, with the reasoning.
tags: [fennec, images, versions]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-01T09:00:00Z }
stale_after: 2026-10-01
---
# Fennec runtime version guidance for images

**Recommended: pinned.** A production image should name an exact Fennec runtime
version, so the image content is a function of its build inputs and nothing else.

## Why pinning is the recommendation

An image whose runtime floats is not reproducible: two builds of the same commit
can differ, and a rollback restores the application without restoring the runtime
it was tested against.

| Treatment | Rebuild reproducible | Rollback restores runtime |
|---|---|---|
| pinned | yes | yes |
| floating | no | no |

## Keeping pins current

Pins rot, and that is a process problem rather than an argument against them: a
weekly job proposes the bump, and the pin moves through the same test gate as any
other change. What must not happen is the runtime moving without a commit that
says so.
