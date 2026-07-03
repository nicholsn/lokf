"""Bundle loading and RDF projection against the reference bundle."""
import pathlib

import pytest

from lokf import load_bundle

BUNDLE = pathlib.Path(__file__).parent.parent / "examples" / "acme-knowledge"


@pytest.fixture(scope="module")
def bundle():
    return load_bundle(BUNDLE)


def test_loads_six_concepts_skipping_reserved(bundle):
    assert len(bundle.concepts) == 6
    assert sorted(c.type for c in bundle.concepts) == [
        "Dataset", "GlossaryTerm", "Metric", "Playbook", "Service", "Table",
    ]


def test_bundle_meta(bundle):
    assert bundle.base_iri == "https://acme.example/knowledge/"
    assert bundle.meta["lokf_version"] == "0.1"


def test_iri_resolution(bundle):
    metric = bundle.get("metrics/weekly-active-users")
    assert metric is not None
    assert bundle.iri(metric) == (
        "https://acme.example/knowledge/metrics/weekly-active-users"
    )
    # Same concept via full IRI and via .md path
    assert bundle.get(bundle.iri(metric)) is metric
    assert bundle.get("metrics/weekly-active-users.md") is metric


def test_graph_matches_committed_projection(bundle):
    g = bundle.graph()
    assert len(g) == 86  # examples/acme-knowledge.nt

    from rdflib import URIRef

    wau = URIRef("https://acme.example/knowledge/metrics/weekly-active-users")
    preds = {str(p) for p in g.predicates(subject=wau)}
    assert "http://www.w3.org/ns/prov#wasDerivedFrom" in preds
    assert "http://purl.org/dc/terms/requires" in preds


def test_concept_body_and_title(bundle):
    term = bundle.get("glossary/active-user")
    assert term.title == "Active User"
    assert "# Definition" in term.body
