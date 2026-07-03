"""Tests for ``lokf.rdf`` — markdown (concept or bundle) to RDF."""
from __future__ import annotations

import pathlib

import pytest
from rdflib import Graph, URIRef

from lokf import rdf

BUNDLE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge"
METRIC = BUNDLE / "metrics" / "weekly-active-users.md"
WAU = URIRef("https://acme.example/knowledge/metrics/weekly-active-users")


@pytest.mark.parametrize("fmt", ["ttl", "nt", "jsonld", "xml"])
def test_serialize_single_concept_is_parseable(fmt):
    """Each format serializes to non-empty text that rdflib can re-parse."""
    text = rdf.serialize(METRIC, fmt=fmt)
    assert isinstance(text, str)
    assert text.strip()
    g = Graph()
    g.parse(data=text, format=rdf._rdflib_format(fmt))
    assert len(g) > 0


def test_graph_of_single_file_has_wau_subject_and_relations():
    """The single metric file yields the WAU subject with prov + dcterms links."""
    g = rdf.graph_of(METRIC)
    preds = {str(p) for s, p, o in g if s == WAU}
    assert str(WAU) in {str(s) for s, _, _ in g}
    assert "http://www.w3.org/ns/prov#wasDerivedFrom" in preds
    assert "http://purl.org/dc/terms/requires" in preds


def test_graph_of_bundle_dir_triple_count():
    """The whole acme bundle projects to exactly 86 triples."""
    g = rdf.graph_of(BUNDLE)
    assert len(g) == 86


def test_unknown_format_raises_value_error():
    """An unrecognized format is rejected by serialize()."""
    with pytest.raises(ValueError):
        rdf.serialize(METRIC, fmt="bogus")


def test_standalone_file_keeps_explicit_id(tmp_path):
    """A concept file outside any bundle keeps its explicit ``id`` as subject."""
    p = tmp_path / "thing.md"
    p.write_text(
        "---\n"
        "type: Metric\n"
        "id: https://x.example/thing\n"
        "title: A Thing\n"
        "---\n\n# Body\n",
        encoding="utf-8",
    )
    g = rdf.graph_of(p)
    subjects = {str(s) for s, _, _ in g}
    assert "https://x.example/thing" in subjects
    # Nothing should be minted under a file:// IRI when an id is given.
    assert not any(s.startswith("file://") for s in subjects)


def test_standalone_file_without_id_gets_file_iri(tmp_path):
    """A standalone concept with no ``id`` falls back to a file:// IRI subject."""
    p = tmp_path / "noid.md"
    p.write_text(
        "---\ntype: Metric\ntitle: No Id\n---\n\n# Body\n",
        encoding="utf-8",
    )
    g = rdf.graph_of(p)
    subjects = {str(s) for s, _, _ in g}
    assert p.resolve().as_uri() in subjects
