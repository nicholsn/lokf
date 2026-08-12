---
type: Metric
id: https://acme.example/knowledge/metrics/weekly-active-users
title: Weekly Active Users
description: Distinct users with at least one qualifying event in a trailing 7-day window.
unit: users
formula: COUNT(DISTINCT user_id) over trailing 7 days WHERE event_name IN qualifying_events
resource: https://looker.acme.example/looks/wau
tags: [growth, engagement, north-star]
created: 2026-01-15T09:00:00Z
version: "2.1"
generated: { by: "human:jsmith@acme", at: 2026-06-30T12:00:00Z }
verified:
  - { by: "human:kliu@acme", at: 2026-07-01T16:00:00Z }
  - { by: "process:metrics-nightly", at: 2026-07-02T02:00:00Z }
status: stable
stale_after: 2026-12-31
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
  - https://acme.example/knowledge/computations/weekly-active-users-count
sources:
  - id: metric-defs-rfc
    resource: https://wiki.acme.example/rfc/metric-defs
    title: Metric definitions RFC
    author: "team:analytics"
    last_modified: 2026-05-12
  - id: wau-look
    resource: https://looker.acme.example/looks/wau
    title: WAU Look (production dashboard)
    author: "team:analytics"
    usage_count: 3200
usage_window: { from: 2026-06-01, to: 2026-06-30 }
---

# Definition

**Weekly Active Users (WAU)** is the count of distinct `user_id`s that produced at
least one [qualifying event](/glossary/active-user.md) during the trailing 7-day
window, computed from [User Events](/tables/user-events.md) by the
[sanctioned WAU computation](/computations/weekly-active-users-count.md).[^metric-defs-rfc]

# Notes

- The window is rolling, not calendar-aligned.
- Internal test accounts are excluded.
- The production figure is served by the WAU Look.[^wau-look]

[^metric-defs-rfc]: Metric definitions RFC
[^wau-look]: WAU Look (production dashboard)
