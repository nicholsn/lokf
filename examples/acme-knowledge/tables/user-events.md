---
type: Table
id: https://acme.example/knowledge/tables/user-events
title: User Events
description: One row per product event emitted by a user.
resource: https://console.cloud.google.com/bigquery?p=acme&d=events&t=user_events
tags: [analytics, events]
timestamp: 2026-06-28T00:00:00Z
isPartOf:
  - https://acme.example/knowledge/datasets/events
fields:
  - name: event_id
    datatype: string
    description: Globally unique event identifier.
    is_key: true
  - name: user_id
    datatype: string
    description: The user who produced the event.
  - name: event_name
    datatype: string
    description: The type of event (e.g. page_view, purchase).
  - name: occurred_at
    datatype: datetime
    description: When the event occurred.
---

# Schema

| Column        | Type      | Description                          |
|---------------|-----------|--------------------------------------|
| `event_id`    | STRING    | Globally unique event identifier.    |
| `user_id`     | STRING    | The user who produced the event.     |
| `event_name`  | STRING    | The type of event.                   |
| `occurred_at` | TIMESTAMP | When the event occurred.             |

Part of the [Events dataset](/datasets/events.md).
