---
type: Reference
title: "Auditing Selkie access"
description: "Answering who can read a bucket, and what an audit has to read to answer it."
tags: [selkie, audit, access]
status: stable
generated: { by: human:okf-bench, at: 2026-09-13T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-09-13T09:00:00Z }
stale_after: 2027-09-30
---
# Auditing Selkie access

## Scope of an audit

Where both apply, **the account policy** is decisive: a bucket may narrow it but
not depart from it. An audit therefore starts from the account policy, which
bounds the answer, and reads bucket policies only to find where access is
narrower than the baseline.

## Running one

`selkie access explain --principal --bucket` evaluates both policies for a
principal and prints which rule decided. Batch mode takes a principal list and
writes one row per principal and bucket.
