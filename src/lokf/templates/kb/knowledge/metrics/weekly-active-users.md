---
type: Metric
title: Weekly Active Users
description: An example metric that measures the Active User term.
unit: users
formula: COUNT(DISTINCT user_id) over a trailing 7-day window
measures: [__KB_BASE_IRI__glossary/active-user]
tags: [example]
---

# Weekly Active Users

An example metric that **measures** the [Active User](../glossary/active-user.md)
term. `measures` is a typed relation — it becomes an edge in the graph (see the
Graph page in the site navigation).
