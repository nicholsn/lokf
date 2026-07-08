"""Tests for the ``lokf`` CLI (Typer) via ``typer.testing.CliRunner``.

Only side-effect-free commands are driven here — convert, query, and vocab.
serve and mcp block, so they are deliberately not invoked.
"""
from __future__ import annotations

import json
import pathlib

from typer.testing import CliRunner

from lokf.cli import app

BUNDLE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge"
METRIC = BUNDLE / "metrics" / "weekly-active-users.md"

_SELECT = "SELECT ?name WHERE { ?m a lokf:Metric ; schema:name ?name }"
_CONSTRUCT = (
    "CONSTRUCT { ?s prov:wasDerivedFrom ?o } WHERE { ?s prov:wasDerivedFrom ?o }"
)

runner = CliRunner()


# -- convert ----------------------------------------------------------------
def test_convert_ttl_contains_metric_curie():
    """convert <metric> -f ttl emits Turtle carrying lokf:Metric."""
    result = runner.invoke(app, ["convert", str(METRIC), "-f", "ttl"])
    assert result.exit_code == 0
    assert "lokf:Metric" in result.stdout


def test_convert_nt_non_empty():
    """convert -f nt emits non-empty N-Triples."""
    result = runner.invoke(app, ["convert", str(METRIC), "-f", "nt"])
    assert result.exit_code == 0
    assert result.stdout.strip()
    # N-Triples lines end in a period.
    assert result.stdout.strip().endswith(".")


def test_convert_jsonld_is_json():
    """convert -f jsonld emits parseable JSON-LD."""
    result = runner.invoke(app, ["convert", str(METRIC), "-f", "jsonld"])
    assert result.exit_code == 0
    doc = json.loads(result.stdout)
    assert doc  # non-empty JSON structure


def test_convert_bad_format_exit_2():
    """An unknown --format exits 2 (ValueError -> typer.Exit(2))."""
    result = runner.invoke(app, ["convert", str(METRIC), "--format", "bogus"])
    assert result.exit_code == 2


def test_convert_output_writes_file(tmp_path):
    """convert -o <file> writes the RDF to that path and confirms on stdout."""
    out = tmp_path / "out.ttl"
    result = runner.invoke(app, ["convert", str(METRIC), "-o", str(out)])
    assert result.exit_code == 0
    assert f"wrote {out}" in result.stdout
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "lokf:Metric" in text


# -- validate ---------------------------------------------------------------
def test_validate_reference_bundle_ok():
    """validate <bundle> assembles and validates against KnowledgeBundle."""
    result = runner.invoke(app, ["validate", str(BUNDLE)])
    assert result.exit_code == 0
    assert "validate against KnowledgeBundle" in result.stdout


def test_validate_missing_bundle_nonzero_exit():
    """A non-existent bundle directory is rejected before validation."""
    result = runner.invoke(app, ["validate", "does-not-exist"])
    assert result.exit_code != 0


# -- query ------------------------------------------------------------------
def test_query_select_table_contains_wau():
    """query <bundle> <SELECT> prints a table with the metric name."""
    result = runner.invoke(app, ["query", str(BUNDLE), _SELECT])
    assert result.exit_code == 0
    assert "Weekly Active Users" in result.stdout
    assert "name" in result.stdout  # column header


def test_query_json_valid():
    """query -f json emits valid SPARQL-results JSON."""
    result = runner.invoke(app, ["query", str(BUNDLE), _SELECT, "-f", "json"])
    assert result.exit_code == 0
    doc = json.loads(result.stdout)
    assert doc["head"]["vars"] == ["name"]
    assert doc["results"]["bindings"][0]["name"]["value"] == "Weekly Active Users"


def test_query_construct_turtle():
    """A CONSTRUCT query prints Turtle."""
    result = runner.invoke(app, ["query", str(BUNDLE), _CONSTRUCT])
    assert result.exit_code == 0
    assert "wasDerivedFrom" in result.stdout or "prov:" in result.stdout


def test_query_malformed_sparql_nonzero_exit():
    """A malformed SPARQL query exits non-zero."""
    result = runner.invoke(app, ["query", str(BUNDLE), "SELEC broken"])
    assert result.exit_code != 0


# -- vocab ------------------------------------------------------------------
def test_vocab_lists_relations():
    """vocab prints the relation vocabulary (known relation names present)."""
    result = runner.invoke(app, ["vocab"])
    assert result.exit_code == 0
    assert "derivedFrom" in result.stdout
    assert "dependsOn" in result.stdout


def test_vocab_json_valid():
    """vocab --json emits a parseable list of relation records."""
    result = runner.invoke(app, ["vocab", "--json"])
    assert result.exit_code == 0
    records = json.loads(result.stdout)
    assert isinstance(records, list) and records
    assert {"name", "curie", "uri"} <= set(records[0])


# -- export -----------------------------------------------------------------
def test_export_writes_graph_and_datasets(tmp_path):
    """export writes graph.json (cytoscape) + datasets.jsonld (Dataset docs)."""
    result = runner.invoke(
        app,
        ["export", str(BUNDLE), "--out-dir", str(tmp_path), "--source-base", "https://x/"],
    )
    assert result.exit_code == 0
    graph = json.loads((tmp_path / "graph.json").read_text())
    assert len(graph["nodes"]) == 6 and len(graph["edges"]) == 8
    assert graph["meta"]["source_base"] == "https://x/"
    datasets = json.loads((tmp_path / "datasets.jsonld").read_text())
    assert len(datasets) == 2 and all(d["@type"] == "Dataset" for d in datasets)
