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
    """The whole acme bundle projects to exactly 153 triples."""
    g = rdf.graph_of(BUNDLE)
    assert len(g) == 153


def test_unknown_type_projects_as_concept_and_keeps_its_spelling(tmp_path):
    """SPEC §8.2: a `type` naming no LOKF class is read as `lokf:Concept`.

    Before, `Skill` minted an undeclared `lokf:Skill` and OKF's spaced
    `BigQuery Table` expanded to an invalid IRI the JSON-LD parser dropped,
    leaving the node with no rdf:type at all. The producer's string now
    survives as `schema:additionalType`, so nothing is lost either way.
    """
    from rdflib import Literal, RDF

    (tmp_path / "index.md").write_text("---\nokf_version: \"0.2\"\n---\n# KB\n", encoding="utf-8")
    (tmp_path / "orders.md").write_text(
        "---\ntype: BigQuery Table\ntitle: Orders\n---\n# Orders\n", encoding="utf-8"
    )
    (tmp_path / "skill.md").write_text(
        "---\ntype: Skill\ntitle: Run\n---\n# Run\n", encoding="utf-8"
    )
    (tmp_path / "wau.md").write_text(
        "---\ntype: Metric\ntitle: WAU\n---\n# WAU\n", encoding="utf-8"
    )
    g = rdf.graph_of(tmp_path)
    concept = URIRef("https://w3id.org/lokf/Concept")
    additional = URIRef("http://schema.org/additionalType")
    typed_concept = {s for s in g.subjects(RDF.type, concept)}
    assert len(typed_concept) == 2
    assert {str(o) for o in g.objects(None, additional)} == {"BigQuery Table", "Skill"}
    # A declared type is untouched: no fallback, no additionalType.
    (metric,) = g.subjects(RDF.type, URIRef("https://w3id.org/lokf/Metric"))
    assert (metric, additional, None) not in g
    assert (metric, RDF.type, concept) not in g
    assert Literal("Metric") not in set(g.objects(None, additional))


def test_revision_projects_as_a_literal_on_the_event(tmp_path):
    """`verified[].revision` lands on the lokf:Verification node as a plain
    literal under lokf:revision - an opaque version token, never an IRI."""
    from rdflib import Literal

    p = tmp_path / "thing.md"
    p.write_text(
        "---\ntype: Metric\nid: https://x.example/thing\n"
        "verified: { by: human:ada, at: 2026-09-17T09:00:00Z, revision: 3f9c2a1 }\n"
        "---\n# T\n",
        encoding="utf-8",
    )
    g = rdf.graph_of(p)
    (event,) = g.objects(URIRef("https://x.example/thing"), URIRef("https://w3id.org/lokf/verified"))
    assert (event, URIRef("https://w3id.org/lokf/revision"), Literal("3f9c2a1")) in g


def test_bare_date_under_a_datetime_slot_projects_as_midnight_utc(tmp_path):
    """`stale_after: 2026-12-31` is read as that day at 00:00:00Z and typed
    xsd:dateTime, the same as OKF's own `2026-12-31T00:00:00Z` spelling."""
    from rdflib import Literal, XSD

    p = tmp_path / "thing.md"
    p.write_text(
        "---\ntype: Metric\nid: https://x.example/thing\nstale_after: 2026-12-31\n---\n# T\n",
        encoding="utf-8",
    )
    g = rdf.graph_of(p)
    (value,) = g.objects(URIRef("https://x.example/thing"), URIRef("http://schema.org/expires"))
    assert value.datatype == XSD.dateTime
    assert value == Literal("2026-12-31T00:00:00+00:00", datatype=XSD.dateTime)


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
