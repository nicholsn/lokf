"""The tabular projection: a bundle -> one table per type + a relations edge table."""
import pathlib

import pytest

pd = pytest.importorskip("pandas")

from lokf.tables import (
    RELATIONS_TABLE,
    external_table_ddl,
    to_frames,
    to_sqlite,
    write_csv,
)

ROOT = pathlib.Path(__file__).parent.parent
BUNDLE = ROOT / "examples" / "acme-knowledge"


@pytest.fixture(scope="module")
def frames():
    return to_frames(BUNDLE)


def test_one_table_per_type_plus_relations(frames):
    # every concept type in the reference bundle becomes a node table
    for t in ["Metric", "Table", "Dataset", "GlossaryTerm", "Service", "Playbook"]:
        assert t in frames, t
    assert RELATIONS_TABLE in frames


def test_scalar_columns_not_relations(frames):
    metric = frames["Metric"]
    assert {"id", "type", "title", "unit"}.issubset(metric.columns)
    assert (metric["title"] == "Weekly Active Users").any()
    # typed-relation slots are edges, never node columns
    assert "derivedFrom" not in metric.columns
    assert "dependsOn" not in metric.columns


def test_relations_edges(frames):
    edges = frames[RELATIONS_TABLE]
    assert {"source", "predicate", "target"}.issubset(edges.columns)
    predicates = set(edges["predicate"])
    assert {"derivedFrom", "dependsOn", "measures"} & predicates
    # the WAU metric was derived from the user-events table
    derived = edges[edges["predicate"] == "derivedFrom"]
    assert derived["target"].str.contains("user-events").any()


def test_list_field_is_scalarized(frames):
    # tags (a multivalued string slot) is joined, not exploded into edges
    metric = frames["Metric"]
    assert "tags" in metric.columns
    assert metric["tags"].str.contains(";").any()


def test_write_csv(tmp_path, frames):
    out = write_csv(frames, tmp_path / "t")
    assert (out / "Metric.csv").exists()
    assert (out / f"{RELATIONS_TABLE}.csv").exists()


def test_sqlite(tmp_path, frames):
    db = to_sqlite(frames, tmp_path / "lokf.db")
    import sqlite3

    con = sqlite3.connect(str(db))
    n = con.execute(f"SELECT COUNT(*) FROM {RELATIONS_TABLE}").fetchone()[0]
    con.close()
    assert n > 0


def test_external_table_ddl_bigquery(frames):
    ddl = external_table_ddl(frames, "bigquery", "gs://bucket/lokf")
    assert "CREATE OR REPLACE EXTERNAL TABLE `lokf.Metric`" in ddl
    assert "format = 'PARQUET'" in ddl
    assert "gs://bucket/lokf/relations.parquet" in ddl


def test_external_table_ddl_athena(frames):
    ddl = external_table_ddl(frames, "athena", "s3://bucket/lokf")
    assert "CREATE EXTERNAL TABLE IF NOT EXISTS Metric" in ddl
    assert "STORED AS PARQUET" in ddl
    assert "LOCATION 's3://bucket/lokf/Metric/'" in ddl


def test_unknown_dialect(frames):
    with pytest.raises(ValueError):
        external_table_ddl(frames, "duckdb")
