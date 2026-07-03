"""Tests for the graph / dataset-search projections in ``lokf.export``."""
from __future__ import annotations

import pathlib

import lokf
from lokf.export import dataset_search_jsonld, to_cytoscape

BUNDLE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge"


def _bundle():
    return lokf.load_bundle(BUNDLE)


def test_cytoscape_matches_rdf_projection():
    """Nodes = concepts; edge set = concept-to-concept subset of the graph."""
    from rdflib import URIRef

    bundle = _bundle()
    vocab = lokf.vocabulary()
    cyto = to_cytoscape(bundle, vocab)

    assert len(cyto["nodes"]) == 6

    iris = {bundle.iri(c) for c in bundle.concepts}
    g = bundle.graph()
    expected = {
        (str(s), str(p), str(o))
        for s, p, o in g
        if isinstance(s, URIRef)
        and isinstance(o, URIRef)
        and str(s) in iris
        and str(o) in iris
    }
    actual = {
        (e["data"]["source"], vocab.expand(e["data"]["predicate"]), e["data"]["target"])
        for e in cyto["edges"]
    }
    assert actual == expected
    assert len(cyto["edges"]) == len(expected)


def test_cytoscape_known_edges_present():
    """Specific typed-relation edges are projected with the right predicate."""
    bundle = _bundle()
    cyto = to_cytoscape(bundle)
    base = bundle.base_iri
    triples = {
        (e["data"]["source"], e["data"]["predicate"], e["data"]["target"])
        for e in cyto["edges"]
    }
    wau = base + "metrics/weekly-active-users"
    events = base + "tables/user-events"
    playbook = base + "playbooks/data-freshness-incident"
    assert (wau, "prov:wasDerivedFrom", events) in triples
    assert (playbook, "schema:about", events) in triples


def test_cytoscape_excludes_body_only_hyperlink():
    """A body markdown link with no typed relation produces no edge."""
    bundle = _bundle()
    cyto = to_cytoscape(bundle)
    base = bundle.base_iri
    active_user = base + "glossary/active-user"
    wau = base + "metrics/weekly-active-users"
    # active-user's body links to WAU, but it declares no typed relation to it.
    assert not any(
        e["data"]["source"] == active_user and e["data"]["target"] == wau
        for e in cyto["edges"]
    )


def test_dataset_search_jsonld():
    """One schema.org Dataset doc per Dataset/Table concept, keys non-empty."""
    bundle = _bundle()
    docs = dataset_search_jsonld(bundle)
    assert len(docs) == 2
    names = {d["name"] for d in docs}
    assert names == {"Events", "User Events"}
    for doc in docs:
        assert doc["@context"] == "https://schema.org/"
        assert doc["@type"] == "Dataset"
        assert doc["name"]
        assert doc["description"]
        assert doc["@id"]
