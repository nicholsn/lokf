---
title: Tables & the lakehouse
description: Project a LOKF bundle to linked tables — DataFrames, Parquet, SQL, or a BigQuery/Athena lakehouse.
---

A LOKF bundle is a graph — and, because it is well-modeled data, it is also a set
of **linked tables**. `lokf tables` projects a bundle to **one table per concept
type** (the nodes) plus a single **`relations`** table (the typed edges:
`source`, `predicate`, `target`).

This is the *abstract* knowledge graph: the same information you can traverse and
reason over in RDF, reshaped so you can analyze it in pandas/polars, join it in
SQL, or scale it in a lakehouse.

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
- Every **typed relation** (`derivedFrom`, `dependsOn`, `memberOf`, `about`, the
  reified `relations`, …) becomes a row in the `relations` edge table.

## Two shapes, one schema

The graph projection (RDF/SPARQL) and the table projection are two views of the
same well-modeled data — both derived from the one LinkML schema. See also the
generated [`lokf.sql`](https://github.com/nicholsn/lokf/blob/main/lokf.sql)
(relational DDL) and the `lokf.datamodel` Python bindings.
