---
type: Reference
title: "Selkie snapshot encryption guidance"
description: "Where snapshot encryption should happen and what each choice means for key custody."
tags: [selkie, snapshots, encryption]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-27T09:00:00Z }
stale_after: 2026-09-30
---
# Selkie snapshot encryption guidance

**Recommended: client-side.** Snapshots should be encrypted before they leave
the producing host, so the store never holds plaintext and never holds the key.

## What the choice decides

| Where | Store sees | Key custody |
|---|---|---|
| client-side | ciphertext | producer |
| server-side | plaintext briefly | store operator |

Key custody is the whole argument. With client-side encryption the store is a
carrier of opaque bytes: a compromise of the store yields ciphertext, and the
blast radius of a storage-side incident stops at availability.

## Operational cost

The producer owns key rotation and must keep old keys readable for as long as
the snapshots they encrypted are retained. That cost is the price of the custody
property above.
