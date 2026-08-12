---
lokf_version: "0.2"
okf_version: "0.2"
base_iri: https://acme.example/knowledge/
context: https://w3id.org/lokf/context.jsonld
title: Acme Knowledge Bundle
description: Canonical, agent-readable knowledge for Acme's data and analytics org.
license: https://creativecommons.org/licenses/by/4.0/
publisher:
  type: Organization
  id: https://acme.example
  name: Acme Corp
---

# Metrics

* [Weekly Active Users](metrics/weekly-active-users.md) - Trailing-7-day distinct active users.

# Datasets

* [Events](datasets/events.md) - All product analytics events.
* [User Events](tables/user-events.md) - One row per product event (table).

# Glossary

* [Active User](glossary/active-user.md) - A user with at least one qualifying event.

# Computations

* [Weekly Active Users count](computations/weekly-active-users-count.md) - The sanctioned, attestable WAU computation.

# References

* [Run on BigQuery](references/skills/run-on-bq.md) - Executor instructions for attested computations.

# Playbooks

* [Data freshness incident response](playbooks/data-freshness-incident.md) - Triage a freshness SLA breach.

# Services

* [Analytics API](services/analytics-api.md) - Query aggregated product metrics.
