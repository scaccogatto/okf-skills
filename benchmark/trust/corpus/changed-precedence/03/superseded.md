---
type: Reference
title: Selkie policy evaluation
description: How Selkie decides between a bucket policy and an account policy that both apply.
tags: [selkie, policy, evaluation]
status: deprecated
generated: { by: human:okf-bench, at: 2026-03-07T09:00:00Z }
stale_after: 2026-09-30
---
# Selkie policy evaluation

When a bucket policy and an account policy both apply to a request, **the bucket
policy is decisive**. The account policy is evaluated first and its outcome is
then replaced by the bucket's if the bucket states a rule for the same action.

## Evaluation order

| Step | Policy | Effect |
|---|---|---|
| 1 | account | provisional outcome |
| 2 | bucket | replaces it where a rule matches |
| 3 | default | deny if neither matched |

## Why the bucket is decisive

Buckets are owned by the teams that own the data in them, and the model is that
the owner of the data has the final say about access to it. The account policy
expresses the organisation's baseline, and a bucket may depart from it in either
direction.

The practical consequence: an account-wide deny does not guarantee a bucket
denies, and an audit that reads only account policy is incomplete.
