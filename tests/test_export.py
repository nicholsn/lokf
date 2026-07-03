"""Tests for the graph / dataset-search projections in ``lokf.export``."""
from __future__ import annotations

import pathlib

import lokf
from lokf.export import dataset_search_jsonld, to_cytoscape

BUNDLE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge"


def _bundle():
    return lokf.load_bundle(BUNDLE)


def _write_synthetic_bundle(tmp_path):
    """A tiny bundle with a reified relation, junk entries, and relative refs."""
    root = tmp_path / "bundle"
    (root / "datasets").mkdir(parents=True)
    (root / "tables").mkdir()
    (root / "index.md").write_text(
        "---\n"
        'lokf_version: "0.1"\n'
        "base_iri: https://kb.example/\n"
        "title: Synthetic bundle\n"
        "---\n\n# Synthetic\n",
        encoding="utf-8",
    )
    (root / "datasets" / "a.md").write_text(
        "---\n"
        "type: Dataset\n"
        "title: A\n"
        "description: Synthetic dataset A.\n"
        "isPartOf:\n"
        "  - datasets/parent\n"
        "relations:\n"
        "  - not-a-mapping\n"
        "  - predicate: joinsWith\n"
        "    target: tables/b\n"
        "  - 42\n"
        "---\n\nBody A.\n",
        encoding="utf-8",
    )
    (root / "tables" / "b.md").write_text(
        "---\n"
        "type: Table\n"
        "title: B\n"
        "description: Synthetic table B.\n"
        "---\n\nBody B.\n",
        encoding="utf-8",
    )
    return lokf.load_bundle(root)


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
    # All acme edges come from named slots, so none is marked reified.
    assert all(e["data"]["reified"] is False for e in cyto["edges"])


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


def test_cytoscape_reified_relation_flattened_and_marked(tmp_path):
    """A reified ``relations:`` entry becomes a display edge with reified=True,
    even though the RDF projection keeps it as a reified statement — the edge
    is deliberately absent from the direct concept-to-concept triple subset."""
    from rdflib import URIRef

    bundle = _write_synthetic_bundle(tmp_path)
    a = "https://kb.example/datasets/a"
    b = "https://kb.example/tables/b"

    cyto = to_cytoscape(bundle)
    edges = [
        e
        for e in cyto["edges"]
        if e["data"]["source"] == a and e["data"]["target"] == b
    ]
    assert len(edges) == 1
    assert edges[0]["data"]["predicate"] == "lokf:joinsWith"
    assert edges[0]["data"]["reified"] is True

    # The documented divergence: in RDF the relation is a reified statement
    # (a blank node with rdf:predicate/rdf:object), not a direct a -> b triple.
    direct = {
        (str(s), str(o))
        for s, _, o in bundle.graph()
        if isinstance(s, URIRef) and isinstance(o, URIRef)
    }
    assert (a, b) not in direct


def test_cytoscape_skips_scalar_relations_entries(tmp_path):
    """Non-dict ``relations:`` entries (strings, numbers) are skipped, and the
    valid entries around them still project."""
    bundle = _write_synthetic_bundle(tmp_path)
    cyto = to_cytoscape(bundle)  # must not raise on the scalar junk
    reified = [e for e in cyto["edges"] if e["data"]["reified"]]
    assert len(reified) == 1
    assert reified[0]["data"]["slot"] == "joinsWith"


def test_dataset_search_jsonld_resolves_relative_ispartof(tmp_path):
    """Bundle-relative isPartOf refs are emitted as absolute IRIs."""
    bundle = _write_synthetic_bundle(tmp_path)
    docs = dataset_search_jsonld(bundle)
    a_doc = next(d for d in docs if d["name"] == "A")
    assert a_doc["isPartOf"] == ["https://kb.example/datasets/parent"]
    # Table is a Dataset subclass, so B gets a doc too (no resource -> url=IRI).
    b_doc = next(d for d in docs if d["name"] == "B")
    assert b_doc["url"] == "https://kb.example/tables/b"


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
