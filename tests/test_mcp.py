"""Tests for the LOKF FastMCP stdio server in ``lokf.mcp_server``.

FastMCP's introspection API is async; sync tests wrap it in ``asyncio.run``
(no pytest-asyncio). The tool functions themselves are plain callables, so the
functional tests invoke them directly against ``examples/acme-knowledge``.
"""
from __future__ import annotations

import asyncio
import json
import pathlib

import lokf.mcp_server as mcp

BUNDLE = str(pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge")

TOOL_NAMES = {
    "list_concepts",
    "describe_concept",
    "sparql_query",
    "convert",
    "propose_relations",
    "get_vocabulary",
    "bundle_summary",
}


def test_server_imports_and_named():
    assert mcp.server.name == "lokf"


def test_seven_tools_registered():
    tools = asyncio.run(mcp.server.list_tools())
    assert {t.name for t in tools} == TOOL_NAMES
    assert len(tools) == 7


def test_list_concepts():
    concepts = mcp.list_concepts(BUNDLE)
    assert len(concepts) == 6
    assert all(
        set(c) == {"concept_id", "type", "title", "iri"} for c in concepts
    )


def test_describe_concept():
    d = mcp.describe_concept(BUNDLE, "metrics/weekly-active-users")
    assert d["type"] == "Metric"
    assert d["turtle"]
    assert "lokf:Metric" in d["turtle"]


def test_describe_concept_not_found():
    assert "error" in mcp.describe_concept(BUNDLE, "no/such-concept")


def test_sparql_select_metrics():
    result = mcp.sparql_query(
        BUNDLE, "SELECT ?m ?t WHERE { ?m a lokf:Metric ; schema:name ?t }"
    )
    assert result["columns"] == ["m", "t"]
    assert result["rows"] == [
        {
            "m": "https://acme.example/knowledge/metrics/weekly-active-users",
            "t": "Weekly Active Users",
        }
    ]


def test_sparql_ask():
    result = mcp.sparql_query(BUNDLE, "ASK { ?s prov:wasDerivedFrom ?o }")
    assert result == {"boolean": True}


def test_sparql_construct():
    result = mcp.sparql_query(
        BUNDLE, "CONSTRUCT { ?s a lokf:Metric } WHERE { ?s a lokf:Metric }"
    )
    assert "turtle" in result
    assert result["turtle"].strip()


def test_sparql_error():
    assert "error" in mcp.sparql_query(BUNDLE, "SELCT nonsense")


def test_convert_dir():
    result = mcp.convert(BUNDLE, "ttl")
    assert result["format"] == "ttl"
    assert "lokf:Metric" in result["rdf"]


def test_convert_bad_format():
    assert "error" in mcp.convert(BUNDLE, "bogus")


def test_propose_relations():
    rows = mcp.propose_relations(BUNDLE)
    assert rows
    for row in rows:
        assert {
            "source",
            "link_text",
            "predicate",
            "curie",
            "confidence",
            "rationale",
        } <= set(row)
        assert "applied" not in row


def test_get_vocabulary():
    vocab = mcp.get_vocabulary()
    assert len(vocab["relations"]) >= 10
    assert "Dataset" in vocab["classes"]
    for rel in vocab["relations"]:
        assert set(rel) == {"name", "curie", "uri", "frontmatter_key", "description"}


def test_bundle_summary():
    summary = mcp.bundle_summary(BUNDLE)
    assert summary["triple_count"] == 86
    assert summary["concept_count"] == 6
    assert summary["relation_edge_count"] == 8


def test_all_tool_results_json_serializable():
    payloads = [
        mcp.list_concepts(BUNDLE),
        mcp.describe_concept(BUNDLE, "metrics/weekly-active-users"),
        mcp.sparql_query(BUNDLE, "SELECT ?m WHERE { ?m a lokf:Metric }"),
        mcp.convert(BUNDLE, "ttl"),
        mcp.propose_relations(BUNDLE),
        mcp.get_vocabulary(),
        mcp.bundle_summary(BUNDLE),
    ]
    json.dumps(payloads)
