---
type: Reference
title: "Thackery bandwidth planning"
description: "Planning link capacity for Thackery workspaces from their upload profile."
tags: [thackery, bandwidth, planning]
status: stable
generated: { by: human:okf-bench, at: 2026-07-05T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-07-05T09:00:00Z }
stale_after: 2027-07-31
---
# Thackery bandwidth planning

Plan the link from the busiest workspace rather than from the average, because
uploads are bursty and the burst is what fills the pipe.

## The arithmetic

A workspace runs 104 concurrent uploads and a chunk stream holds about 6 Mbit/s,
so one busy workspace needs roughly 620 Mbit/s and two of them saturate a
gigabit link. Size for the number of workspaces that are busy at once, not for
the number that exist.

## Headroom

Leave 30% headroom for commit traffic, which is small per upload and arrives in
a burst at the end of each one.
