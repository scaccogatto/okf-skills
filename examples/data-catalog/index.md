---
okf_version: "0.3"
title: Northwind Grocers analytics catalog
description: >-
  Tables, metrics, policies and runbooks of the Northwind Grocers retail
  analytics warehouse. Use it when answering questions about orders, basket
  size, or how long sales data is kept.
license: CC-BY-4.0
---

# Northwind Grocers analytics catalog

A small example bundle outside software: the knowledge around a fictional
grocery chain's analytics warehouse. It holds a dataset and its tables, a metric
whose number comes from an Attested Computation, a data retention policy, a
glossary term and a runbook for a data incident. The trust signals differ on
purpose: one concept is confirmed by a person, one by an automated check, the
rest are unverified. One table is deprecated, and one metric is past its review
date.

> Render it: `uv run skills/visualize/scripts/okf_visualize.py examples/data-catalog`

# Datasets

* [Sales dataset](datasets/sales.md): the BigQuery dataset for store and online sales.

# Tables

* [Orders](tables/orders.md): one row per completed order, loaded hourly.
* [Orders (legacy)](tables/orders-legacy.md): the old daily export, deprecated.

# Metrics

* [Average basket size](metrics/average-basket-size.md): mean order value per week.

# Computations

* [Weekly average basket size](computations/weekly-basket-size.md): the sanctioned query behind the metric.

# Policies

* [Sales data retention](policies/data-retention.md): how long order data is kept.

# Glossary

* [Basket](glossary/basket.md): what counts as one basket.

# Runbooks

* [Late orders load](runbooks/late-orders-load.md): what to do when the hourly load falls behind.

# References

* [Run a computation on BigQuery](references/run-on-bigquery.md): executor instructions.
