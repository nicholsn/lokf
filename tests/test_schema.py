"""Vocabulary derivation from lokf.yaml."""
import pytest

from lokf.schema import load_context, load_schema, vocabulary


@pytest.fixture(scope="module")
def vocab():
    return vocabulary()


def test_relation_slots_discovered(vocab):
    # The ten Concept-level typed-relation keys plus Metric's `measures`.
    assert set(vocab.relation_slots) == {
        "isPartOf", "hasPart", "references", "dependsOn", "derivedFrom",
        "about", "sameAs", "relatedTo", "definedBy", "source", "measures",
    }
    assert vocab.relation_slots["derivedFrom"].curie == "prov:wasDerivedFrom"
    assert vocab.relation_slots["dependsOn"].uri == "http://purl.org/dc/terms/requires"


def test_relation_slot_domains(vocab):
    assert vocab.relation_slots["derivedFrom"].domains == {"Concept"}
    assert vocab.relation_slots["measures"].domains == {"Metric"}


def test_relation_types_cover_slots_plus_reified(vocab):
    assert set(vocab.relation_slots) < set(vocab.relation_types)
    assert vocab.relation_types["joinsWith"].is_slot is False
    assert vocab.relation_types["measures"].curie == "lokf:measures"


def test_expand_and_compact_roundtrip(vocab):
    assert vocab.expand("schema:about") == "http://schema.org/about"
    assert vocab.compact("http://schema.org/about") == "schema:about"
    assert vocab.expand("noprefix") == "noprefix"


def test_classes_have_uris(vocab):
    assert vocab.classes["Dataset"] == "schema:Dataset"
    assert vocab.classes["Metric"] == "lokf:Metric"


def test_context_has_authoring_aliases():
    ctx = load_context()
    assert ctx["type"] == "@type"
    assert ctx["id"] == "@id"


def test_schema_loads():
    schema = load_schema()
    assert schema["name"] == "lokf" or "lokf" in schema.get("id", "")
