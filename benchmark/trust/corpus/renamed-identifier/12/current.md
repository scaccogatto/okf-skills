---
type: Reference
title: "The Ashgrove SDK"
description: "Using the Ashgrove SDK: configuration, tenancy and error handling."
tags: [ashgrove, sdk, clients]
status: stable
generated: { by: human:okf-bench, at: 2026-06-14T09:00:00Z }
verified: { by: human:okf-bench, at: 2026-06-14T09:00:00Z }
stale_after: 2027-05-31
---
# The Ashgrove SDK

Configure once with a token and an organisation, and the SDK handles the rest of
the request envelope.

## Tenancy

`Client(token=..., org=...)` sets `ashgrove-org-id` on every request, so callers
do not assemble the header themselves. Constructing a second client is how you
talk to a second tenancy; the field is not mutable on a live client.

## Errors

A 403 means the token is valid but not for that tenancy, which is almost always
a client constructed with the wrong organisation rather than a permissions
problem.
