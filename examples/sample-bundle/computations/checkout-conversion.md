---
type: Attested Computation
title: Checkout conversion for a window
description: The sanctioned query behind the checkout conversion metric.
tags: [kpi, checkout, sql]
status: stable
runtime: postgres
parameters:
  - { name: window_start, type: timestamp, required: true }
  - { name: window_end, type: timestamp, required: true }
executor:
  resource: /references/run-on-orders-db.md
  receipt: [query_id, executed_sql, result]
attester:
  resource: /references/sql-equality.py
generated: { by: doc_agent/1.0, at: "2026-06-18T12:30:00Z" }
verified: { by: human:dana, at: "2026-06-19T09:00:00Z" }
stale_after: 2026-12-31
sources:
  - id: conversion-def
    resource: /metrics/checkout-conversion.md
    title: Checkout conversion metric definition
    author: human:dana
    last_modified: 2026-06-18
---

# Computation

    SELECT count(*) FILTER (WHERE status = 'paid')::numeric
           / nullif(count(*), 0) AS checkout_conversion
    FROM orders
    WHERE created_at >= :window_start AND created_at < :window_end

Runs against the [Orders database](/datasets/orders-db.md). The denominator is
every order row created in the window, per the metric definition.[^conversion-def]
An agent may supply values for `window_start` and `window_end` and nothing else —
the query itself is not the agent's to write, which is what makes "did the
sanctioned thing run" a mechanical check rather than a judgement call.

[^conversion-def]: Checkout conversion metric definition
