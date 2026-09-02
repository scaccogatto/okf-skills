---
type: Reference
title: "Pellworm deployment checklist"
description: "The checklist a Pellworm deployment runs through, from health gate to traffic shift."
tags: [pellworm, deployments, checklist]
status: stable
generated: { by: human:okf-bench, at: 2026-09-29T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-29T09:00:00Z }
stale_after: 2027-10-31
---
# Pellworm deployment checklist

Five steps per instance, in order.

1. Health gate: the instance reports ready and its pool is allocated.
2. Warming: none. The recommended strategy is lazy, so the instance takes
   traffic cold and fills from the shared entry pool as requests arrive.
3. Traffic shift: 5%, then 50%, then full, with two minutes between steps.
4. Error gate: roll back if the error rate exceeds the pre-shift rate by 1pp.
5. Census: publish the instance's key census for capacity reporting.
