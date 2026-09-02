---
type: Reference
title: Selkie bucket storage classes
description: Storage class applied to a new Selkie store bucket and what each class costs to read.
tags: [selkie, store, storage-class]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-25T09:00:00Z }
stale_after: 2026-10-15
---
# Selkie bucket storage classes

A new Selkie store bucket is created in the **standard** storage class. Objects
are placed on the hot tier at write and stay there until a lifecycle rule moves
them.

## What the standard class buys

The standard class serves a first-byte read from the hot tier with no
rehydration step, which is what makes it the right default for a bucket whose
access pattern is unknown at creation time.

| Class | First-byte read | Rehydration | Storage price |
|---|---|---|---|
| standard | ~8 ms | none | 1.0x |
| infrequent | ~8 ms after rehydration | one pass per object | 0.4x |

## Choosing a class

`storage_class` at create time takes either value, and a lifecycle rule can move
objects between them afterwards. The class is a property of the object rather
than of the bucket, so a bucket may hold both at once and its default only
decides where a new object lands.
