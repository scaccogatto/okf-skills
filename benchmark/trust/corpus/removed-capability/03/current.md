---
type: Reference
title: Daemon lifecycle notes
description: Current lifecycle operations for the Halcyon daemon.
tags: [halcyon, lifecycle, operations]
status: stable
generated: { by: human:okf-bench, at: 2026-09-19T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-19T09:00:00Z }
stale_after: 2027-10-31
---
# Daemon lifecycle notes

Signal-driven reload was removed when configuration moved into the typed store:
a configuration change is picked up by a restart, and the signal is ignored.

Restarts are drain-first, so the operation is no longer disruptive enough to
justify keeping the reload path.
