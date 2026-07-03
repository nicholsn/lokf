---
type: Metric
id: https://acme.example/knowledge/metrics/weekly-active-users
title: Weekly Active Users
description: Distinct users with at least one qualifying event in a trailing 7-day window.
unit: users
formula: COUNT(DISTINCT user_id) over trailing 7 days WHERE event_name IN qualifying_events
resource: https://looker.acme.example/looks/wau
tags: [growth, engagement, north-star]
timestamp: 2026-06-30T12:00:00Z
created: 2026-01-15T09:00:00Z
version: "2.1"
author:
  - type: Person
    id: https://acme.example/people/jsmith
    name: Jordan Smith
    email: jsmith@acme.example
measures:
  - https://acme.example/knowledge/glossary/active-user
derivedFrom:
  - https://acme.example/knowledge/tables/user-events
dependsOn:
  - https://acme.example/knowledge/glossary/active-user
citations:
  - title: Metric definitions RFC
    url: https://wiki.acme.example/rfc/metric-defs
---

# Definition

**Weekly Active Users (WAU)** is the count of distinct `user_id`s that produced at
least one [qualifying event](/glossary/active-user.md) during the trailing 7-day
window, computed from [User Events](/tables/user-events.md).

# Notes

- The window is rolling, not calendar-aligned.
- Internal test accounts are excluded.

# Citations

[1] [Metric definitions RFC](https://wiki.acme.example/rfc/metric-defs)
