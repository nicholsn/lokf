---
type: Playbook
id: https://acme.example/knowledge/playbooks/data-freshness-incident
title: Data freshness incident response
description: Triage steps when the events pipeline lags its freshness SLA.
tags: [oncall, incident]
timestamp: 2026-05-10T00:00:00Z
about:
  - https://acme.example/knowledge/tables/user-events
references:
  - https://acme.example/knowledge/metrics/weekly-active-users
---

# Trigger

A freshness alert fires when [User Events](/tables/user-events.md) lags more than
30 minutes behind its SLA.

# Steps

1. Check the ingestion job dashboard.
2. Confirm whether [Weekly Active Users](/metrics/weekly-active-users.md) is affected.
3. Escalate to the data platform on-call if lag exceeds 2 hours.
