---
title: Tables & the lakehouse
description: Project a LOKF bundle to linked tables — DataFrames, Parquet, SQL, or a BigQuery/Athena lakehouse.
---

A LOKF bundle is a graph — and, because it is well-modeled data, it is also a set
of **linked tables**. `lokf tables` projects a bundle to **one table per concept
type** (the nodes) plus a single **`relations`** table (the typed edges:
`source`, `predicate`, `target`).

Use the type tables for analysis in pandas or polars. Join them with the
relations table in SQL to follow links between records.

## Install

The tabular writers need pandas (and pyarrow for Parquet), which live in an extra:

```bash
pip install "lokf[tables]"
```

## Command

```bash
# DataFrames as CSV or Parquet — one file per type, plus relations
lokf tables examples/acme-knowledge --format csv     --output build/tables
lokf tables examples/acme-knowledge --format parquet --output build/tables

# a SQLite database with one table per type
lokf tables examples/acme-knowledge --format sqlite  --output build/lokf.db

# land Parquet + print CREATE EXTERNAL TABLE DDL to register a lakehouse
lokf tables examples/acme-knowledge --format bigquery --location gs://bucket/lokf
lokf tables examples/acme-knowledge --format athena   --location s3://bucket/lokf
```

Use `--engine polars` if you prefer polars (install it alongside).

## In Python

```python
from lokf.tables import to_frames, external_table_ddl

frames = to_frames("examples/acme-knowledge")   # {"Metric": df, ..., "relations": df}
frames["relations"].head()                       # source | predicate | target
print(external_table_ddl(frames, "bigquery", "gs://bucket/lokf"))
```

## How it maps

- Each concept's **scalar** frontmatter (`title`, `unit`, `roleName`, …) becomes a
  column on its type's table. Multivalued strings like `tags` are joined into one
  cell.
- Core relation slots such as `derivedFrom`, `dependsOn`, and `memberOf`, and
  explicit entries under `relations`, become rows in the edge table.
- A project-specific frontmatter key becomes a column, including when the
  project's domain vocabulary defines it as a relation. To project those
  keys as graph edges or use them in navigation tables, use `lokf export`.
  [Navigation views](/reference/declarative-views/)

## Two shapes, one schema

The graph projection (RDF/SPARQL) and the table projection are two views of the
same well-modeled data — both derived from the one LinkML schema. See also the
generated [`lokf.sql`](https://github.com/nicholsn/lokf/blob/main/lokf.sql)
(relational DDL) and the `lokf.datamodel` Python bindings.
