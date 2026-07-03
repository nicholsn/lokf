"""Tests for ``lokf.store.GraphStore`` — SPARQL over a LOKF knowledge base."""
from __future__ import annotations

import json
import pathlib

from rdflib import Graph

from lokf import rdf
from lokf.store import GraphStore

BUNDLE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge"

# A SELECT for the metric name, relying on the preset schema prefixes.
_METRIC_NAME = "SELECT ?name WHERE { ?m a lokf:Metric ; schema:name ?name }"


def _store():
    return GraphStore.from_bundle(BUNDLE)


def test_from_bundle_triple_count():
    """Loading the acme bundle gives 86 triples."""
    assert len(_store()) == 86


def test_select_returns_dict_rows_with_lexical_values():
    """select() yields ``{var: lexical}`` dicts; the metric name is a string."""
    rows = _store().select(_METRIC_NAME)
    assert rows == [{"name": "Weekly Active Users"}]
    assert isinstance(rows[0]["name"], str)


def test_select_keeps_unbound_variables_as_none():
    """Every selected variable is a column; an unbound one is present as None,
    so a variable unbound in all rows is never silently dropped."""
    rows = _store().select(
        "SELECT ?name ?missing WHERE { "
        "?m a lokf:Metric ; schema:name ?name . "
        "OPTIONAL { ?m lokf:nonexistentSlot ?missing } }"
    )
    assert rows == [{"name": "Weekly Active Users", "missing": None}]


def test_ask_true_and_false():
    """ask() returns the boolean for both a satisfiable and a false pattern."""
    store = _store()
    assert store.ask("ASK { ?m a lokf:Metric }") is True
    assert store.ask("ASK { ?m a lokf:Nonexistent }") is False


def test_construct_turtle_parseable_with_expected_triple():
    """construct() emits Turtle carrying the WAU wasDerivedFrom triple."""
    ttl = _store().construct(
        "CONSTRUCT { ?s prov:wasDerivedFrom ?o } "
        "WHERE { ?s prov:wasDerivedFrom ?o }"
    )
    g = Graph()
    g.parse(data=ttl, format="turtle")
    from rdflib import URIRef
    from rdflib.namespace import PROV

    wau = URIRef("https://acme.example/knowledge/metrics/weekly-active-users")
    events = URIRef("https://acme.example/knowledge/tables/user-events")
    assert (wau, PROV.wasDerivedFrom, events) in g


def test_serialize_results_json_is_valid_sparql_json():
    """serialize_results() returns SPARQL-results JSON with head/results."""
    raw = _store().serialize_results(_METRIC_NAME, "json")
    assert isinstance(raw, bytes)
    doc = json.loads(raw)
    assert doc["head"]["vars"] == ["name"]
    binding = doc["results"]["bindings"][0]["name"]
    assert binding["value"] == "Weekly Active Users"


def test_prefixes_auto_applied_without_prefix_block():
    """Queries using lokf:/schema:/prov: work with no PREFIX block."""
    store = _store()
    assert {"lokf", "schema", "prov"} <= set(store.prefixes)
    # No PREFIX line, yet the CURIEs resolve.
    assert store.ask(
        "ASK { ?m a lokf:Metric ; prov:wasDerivedFrom ?t . "
        "?t a schema:Dataset }"
    ) in (True, False)  # resolves without raising
    rows = store.select("SELECT ?m WHERE { ?m a lokf:Metric }")
    assert len(rows) == 1


def test_rdflib_graph_round_trips_to_86_triples():
    """rdflib_graph() with no query returns the full 86-triple store."""
    g = _store().rdflib_graph()
    assert isinstance(g, Graph)
    assert len(g) == 86


def test_from_graph_and_from_rdf():
    """from_graph and from_rdf build equivalent stores to from_bundle."""
    g = rdf.graph_of(BUNDLE)
    from_graph = GraphStore.from_graph(g)
    assert len(from_graph) == 86

    from_rdf = GraphStore.from_rdf(g.serialize(format="nt"))
    assert len(from_rdf) == 86
    assert from_rdf.select(_METRIC_NAME) == [{"name": "Weekly Active Users"}]
