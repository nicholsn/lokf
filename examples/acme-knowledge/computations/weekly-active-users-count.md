---
type: AttestedComputation
id: https://acme.example/knowledge/computations/weekly-active-users-count
title: Weekly Active Users count
description: The sanctioned computation of WAU for a trailing 7-day window ending on a given day.
tags: [growth, engagement]
runtime: bigquery
parameters:
  - { name: week_end, type: date, required: true }
executor:
  resource: references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: references/attesters/sql_equality.py
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-06-28T14:00:00Z }
verified: { by: "human:jsmith@acme", at: 2026-07-01T09:00:00Z }
status: stable
stale_after: 2026-12-31
sources:
  - id: metric-defs-rfc
    resource: https://wiki.acme.example/rfc/metric-defs
    title: Metric definitions RFC
    author: "team:analytics"
    last_modified: 2026-05-12
about:
  - https://acme.example/knowledge/glossary/active-user
derivedFrom:
  - https://acme.example/knowledge/tables/user-events
relatedTo:
  - https://acme.example/knowledge/metrics/weekly-active-users
---

# Computation

    SELECT COUNT(DISTINCT user_id) AS wau
    FROM `acme.events.user_events`
    WHERE event_name IN UNNEST(@qualifying_events)
      AND DATE(event_ts) BETWEEN DATE_SUB(@week_end, INTERVAL 6 DAY) AND @week_end

The computation binds only the declared parameters; qualifying events are
fixed by the metric definitions RFC.[^metric-defs-rfc] Backs the
[Weekly Active Users](/metrics/weekly-active-users.md) metric.

[^metric-defs-rfc]: Metric definitions RFC
