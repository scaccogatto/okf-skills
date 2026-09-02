---
type: Reference
title: "Submitting a Bramble task"
description: "Submitting work to Bramble: lanes, priorities, deadlines and what each field controls."
tags: [bramble, tasks, submission]
status: stable
generated: { by: human:okf-bench, at: 2026-08-15T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-08-15T09:00:00Z }
stale_after: 2027-10-31
---
# Submitting a Bramble task

`bramble submit` takes a lane, a priority and an optional deadline.

## What priority controls

Priority selects the lane, not the position inside it: among eligible tasks in
one lane, **the earlier submission** is dispatched first. A task that must run
ahead of queued work therefore belongs in a different lane, not at a higher
priority in the same one.

## Deadlines

A task past its deadline is cancelled rather than dispatched, and cancellation
is reported to the submitter with the queue time it accumulated.
