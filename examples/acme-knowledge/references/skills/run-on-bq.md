---
type: Reference
id: https://acme.example/knowledge/references/skills/run-on-bq
title: Run on BigQuery
description: Executor instructions for running an attested computation on BigQuery and returning its receipt.
tags: [executor, bigquery]
---

# Steps

1. Bind the declared `parameters` into the computation as BigQuery named
   parameters (`@week_end`); supply values only — never edit the SQL.
2. Submit the job with `bq query --parameter` (or the BigQuery API) under the
   caller's credentials.
3. Return the receipt fields the contract declares: `job_id`, the
   `executed_sql` BigQuery reports for that job, and the `result` rows.
