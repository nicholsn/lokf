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
    """The whole acme bundle projects to exactly 157 triples."""
    g = rdf.graph_of(BUNDLE)
    assert len(g) == 157


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


@pytest.mark.parametrize("single_file", [False, True])
def test_who_a_concept_is_written_for_projects_under_schema_org(tmp_path, single_file):
    """`typicalAgeRange` is a schema.org literal, and `audience` a node with
    schema.org's age properties as typed integers."""
    from rdflib import Literal
    from rdflib.namespace import RDF, XSD

    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\n---\n# KB\n", encoding="utf-8"
    )
    (tmp_path / "pen.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: The pen\ntypicalAgeRange: 13-18\n"
        "audience:\n  audienceType: students\n  suggestedMinAge: 13\n---\n# The pen\n",
        encoding="utf-8",
    )
    g = rdf.graph_of(tmp_path / "pen.md" if single_file else tmp_path)
    sdo = "http://schema.org/"
    pen = URIRef("https://ex.org/kb/pen")
    assert (pen, URIRef(sdo + "typicalAgeRange"), Literal("13-18")) in g
    audience = g.value(pen, URIRef(sdo + "audience"))
    assert audience is not None
    assert (audience, RDF.type, URIRef(sdo + "PeopleAudience")) in g
    assert (audience, URIRef(sdo + "suggestedMinAge"), Literal(13, datatype=XSD.integer)) in g
    assert (audience, URIRef(sdo + "audienceType"), Literal("students")) in g


def test_audience_projection_preserves_explicit_types_and_custom_properties():
    from rdflib.namespace import RDF

    doc = {
        "id": "https://ex.org/term", "type": "GlossaryTerm",
        "audience": {"type": "https://ex.org/SpecialAudience", "audienceType": "students"},
    }
    g = rdf.docs_to_graph([doc])
    audience = g.value(URIRef(doc["id"]), URIRef("http://schema.org/audience"))
    assert set(g.objects(audience, RDF.type)) == {URIRef("https://ex.org/SpecialAudience")}

    from lokf.schema import load_context

    context = {**load_context(), "audience": {"@id": "https://ex.org/otherAudience"}}
    doc["audience"] = {"audienceType": "students"}
    g = rdf.docs_to_graph([doc], context=context)
    audience = g.value(URIRef(doc["id"]), URIRef("https://ex.org/otherAudience"))
    assert audience is not None
    assert not list(g.objects(audience, RDF.type))


def test_replacement_multiple_successors_and_reference_checks(tmp_path):
    from lokf.model import load_bundle
    (tmp_path / "index.md").write_text("---\nbase_iri: https://example.org/\ntitle: KB\n---\n")
    (tmp_path / "old.md").write_text("---\ntype: Service\ntitle: Old\nstatus: deprecated\nisReplacedBy: [new, split]\n---\n")
    (tmp_path / "new.md").write_text("---\ntype: Service\ntitle: New\n---\n")
    graph = rdf.graph_of(tmp_path)
    predicate = URIRef("http://purl.org/dc/terms/isReplacedBy")
    assert set(graph.objects(URIRef("https://example.org/old"), predicate)) == {
        URIRef("https://example.org/new"), URIRef("https://example.org/split")}
    assert load_bundle(tmp_path).dangling_refs() == [("old", "isReplacedBy", "split")]


def test_exclusions_project_apart_from_sources(tmp_path):
    """A material left out is lokf:excludes with its reason, never schema:isBasedOn."""
    from rdflib import Literal

    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\n---\n# KB\n", encoding="utf-8"
    )
    (tmp_path / "map.md").write_text(
        "---\ntype: Playbook\ntitle: Source map\nsources:\n  - resource: docs/a.md\n"
        "exclusions:\n  - resource: tests\n    reason: behavioural tests\n    by: human:jsmith\n"
        "---\n# Map\n",
        encoding="utf-8",
    )
    g = rdf.graph_of(tmp_path)
    lokf, sdo = "https://w3id.org/lokf/", "http://schema.org/"
    concept = URIRef("https://ex.org/kb/map")
    excluded = g.value(concept, URIRef(lokf + "excludes"))
    assert (excluded, URIRef(lokf + "reason"), Literal("behavioural tests")) in g
    assert (excluded, URIRef("http://www.w3.org/ns/prov#wasAssociatedWith"), Literal("human:jsmith")) in g
    based_on = {str(g.value(o, URIRef(sdo + "url"))) for o in g.objects(concept, URIRef(sdo + "isBasedOn"))}
    assert based_on == {"docs/a.md"}


def test_serialize_is_byte_stable_with_blank_nodes():
    """Blank nodes are labelled from content, so the same input gives the same bytes."""
    bundle = pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge"
    for fmt in ("nt", "ttl"):
        assert rdf.serialize(bundle, fmt) == rdf.serialize(bundle, fmt)


def test_relabel_keeps_nodes_apart_that_differ_only_in_term_kind():
    """A plain "1", a typed 1 and the IRI <1> hash apart, so each blank node
    keeps one label whatever ids rdflib minted for it."""
    import json as _json

    from rdflib import Graph

    doc = {
        "@context": {"ex": "http://ex/", "xsd": "http://www.w3.org/2001/XMLSchema#"},
        "@id": "http://ex/s",
        "ex:q": [{"ex:p": "1"}, {"ex:p": {"@value": "1", "@type": "xsd:integer"}},
                 {"ex:p": {"@id": "http://ex/1"}},
                 # parents that differ only through such children
                 {"ex:r": {"ex:p": "2"}}, {"ex:r": {"ex:p": {"@value": "2", "@type": "xsd:integer"}}}],
    }
    outs = {
        "\n".join(sorted(rdf.relabel_bnodes(Graph().parse(data=_json.dumps(doc), format="json-ld"))
                         .serialize(format="nt").splitlines()))
        for _ in range(12)
    }
    assert len(outs) == 1

