"""Project a LOKF bundle to a set of linked tables — the tabular counterpart to
its RDF graph.

A bundle becomes **one table per concept type** (the nodes) plus a single
``relations`` table (the typed edges: ``source``, ``predicate``, ``target``).
From there the same well-modeled data is analysable as DataFrames, landable as
CSV/Parquet, persistable as SQL, or registerable as a lakehouse via
``CREATE EXTERNAL TABLE`` DDL for BigQuery or Athena.

pandas (and, optionally, polars / pyarrow) are only needed here, so they live in
the ``tables`` extra::

    pip install "lokf[tables]"
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

from lokf.model import Bundle, load_bundle
from lokf.schema import vocabulary

#: Name of the edge table that holds every typed relation in the bundle.
RELATIONS_TABLE = "relations"


def _make_frame(rows: list[dict], engine: str):
    """Build a DataFrame of *rows* with the chosen engine (pandas | polars)."""
    if engine == "polars":
        try:
            import polars as pl
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise ModuleNotFoundError(
                "engine='polars' needs polars: pip install polars."
            ) from exc
        return pl.DataFrame(rows)
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "lokf.tables needs pandas (and pyarrow for Parquet). "
            "Install the extra: pip install 'lokf[tables]'."
        ) from exc
    return pd.DataFrame(rows)


def _scalarize(value: Any) -> Any:
    """Flatten a non-relation frontmatter value into a single table cell."""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return value


def _split(doc: dict, rel_slots: set[str]) -> tuple[dict, list[dict]]:
    """Split one concept into a (node row, edge rows) pair.

    Concept-ranged relation slots (and reified ``relations``) become edges;
    everything else is a scalar column on the node's type table.
    """
    source = doc.get("id")
    node: dict[str, Any] = {}
    edges: list[dict] = []
    for key, value in doc.items():
        if key in rel_slots:
            for target in value if isinstance(value, list) else [value]:
                edges.append({"source": source, "predicate": key, "target": target})
        elif key == "relations":  # reified Relation objects
            for rel in value or []:
                edges.append({
                    "source": source,
                    "predicate": rel.get("predicate"),
                    "target": rel.get("target"),
                })
        else:
            node[key] = _scalarize(value)
    return node, edges


def to_frames(bundle: Bundle | str | pathlib.Path, engine: str = "pandas") -> dict:
    """Project *bundle* to ``{type_name: nodes_frame, "relations": edges_frame}``.

    *bundle* may be a loaded :class:`~lokf.model.Bundle` or a path to a bundle
    directory. One frame per concept ``type`` holds that type's scalar fields;
    the ``relations`` frame holds every typed edge as ``(source, predicate,
    target)``.
    """
    if not isinstance(bundle, Bundle):
        bundle = load_bundle(bundle)
    rel_slots = set(vocabulary().relation_slots)
    by_type: dict[str, list[dict]] = {}
    edges: list[dict] = []
    for doc in bundle.docs():
        node, doc_edges = _split(doc, rel_slots)
        by_type.setdefault(str(doc.get("type", "Concept")), []).append(node)
        edges.extend(doc_edges)
    frames = {name: _make_frame(rows, engine) for name, rows in by_type.items()}
    frames[RELATIONS_TABLE] = _make_frame(edges, engine)
    return frames


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------
def _to_pandas(df):
    return df.to_pandas() if hasattr(df, "to_pandas") else df


def write_csv(frames: dict, outdir) -> pathlib.Path:
    """Write each frame to ``outdir/<name>.csv``."""
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in frames.items():
        if hasattr(df, "write_csv"):  # polars
            df.write_csv(str(out / f"{name}.csv"))
        else:
            df.to_csv(out / f"{name}.csv", index=False)
    return out


def write_parquet(frames: dict, outdir) -> pathlib.Path:
    """Write each frame to ``outdir/<name>.parquet`` (needs pyarrow)."""
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in frames.items():
        if hasattr(df, "write_parquet"):  # polars
            df.write_parquet(str(out / f"{name}.parquet"))
        else:
            df.to_parquet(out / f"{name}.parquet")
    return out


def to_sqlite(frames: dict, path) -> pathlib.Path:
    """Write every frame as a table in a SQLite database at *path*."""
    import sqlite3

    path = pathlib.Path(path)
    con = sqlite3.connect(str(path))
    try:
        for name, df in frames.items():
            _to_pandas(df).to_sql(name, con, if_exists="replace", index=False)
    finally:
        con.close()
    return path


# ---------------------------------------------------------------------------
# External-table DDL (the lakehouse story)
# ---------------------------------------------------------------------------
_BQ_TYPE = {
    "object": "STRING", "string": "STRING", "str": "STRING",
    "int64": "INT64", "Int64": "INT64",
    "float64": "FLOAT64", "float": "FLOAT64",
    "bool": "BOOL", "boolean": "BOOL",
    "datetime64[ns]": "TIMESTAMP",
}
_ATHENA_TYPE = {
    "STRING": "string", "INT64": "bigint", "FLOAT64": "double",
    "BOOL": "boolean", "TIMESTAMP": "timestamp",
}


def _columns(df) -> list[tuple[str, str]]:
    """(column, BigQuery type) pairs inferred from a frame's dtypes."""
    if hasattr(df, "dtypes") and hasattr(df.dtypes, "items"):  # pandas
        items = [(c, str(t)) for c, t in df.dtypes.items()]
    else:  # polars
        items = [(c, str(t).lower()) for c, t in df.schema.items()]
    return [(c, _BQ_TYPE.get(t, "STRING")) for c, t in items]


def external_table_ddl(frames: dict, dialect: str = "bigquery",
                       location: str = "gs://your-bucket/lokf",
                       dataset: str = "lokf") -> str:
    """``CREATE EXTERNAL TABLE`` DDL registering the bundle's Parquet as a lakehouse.

    Pair with :func:`write_parquet` (land the files at *location*), then run this
    DDL to expose one external table per concept type + the relations table.
    """
    base = location.rstrip("/")
    stmts = []
    for name, df in frames.items():
        cols = _columns(df)
        if dialect == "bigquery":
            defs = ",\n  ".join(f"`{c}` {t}" for c, t in cols)
            stmts.append(
                f"CREATE OR REPLACE EXTERNAL TABLE `{dataset}.{name}` (\n  {defs}\n)\n"
                f"OPTIONS (format = 'PARQUET', uris = ['{base}/{name}.parquet']);"
            )
        elif dialect == "athena":
            defs = ",\n  ".join(f"`{c}` {_ATHENA_TYPE.get(t, 'string')}" for c, t in cols)
            stmts.append(
                f"CREATE EXTERNAL TABLE IF NOT EXISTS {name} (\n  {defs}\n)\n"
                f"STORED AS PARQUET\nLOCATION '{base}/{name}/';"
            )
        else:
            raise ValueError(f"unknown dialect: {dialect!r} (use 'bigquery' or 'athena')")
    return "\n\n".join(stmts)
