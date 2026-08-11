---
type: Service
id: https://acme.example/knowledge/services/analytics-api
title: Analytics API
description: REST API for querying aggregated product metrics.
endpoint: https://api.acme.example/v2/analytics
http_method: GET
documentation: https://developers.acme.example/analytics
tags: [api, analytics]
timestamp: 2026-06-01T00:00:00Z
verified: { by: "process:api-contract-tests", at: 2026-06-02T04:00:00Z }
stale_after: 2026-07-01
about:
  - https://acme.example/knowledge/metrics/weekly-active-users
---

# Overview

The Analytics API returns aggregated values for metrics such as
[Weekly Active Users](/metrics/weekly-active-users.md).
