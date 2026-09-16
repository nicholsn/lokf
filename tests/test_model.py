"""Bundle loading and RDF projection against the reference bundle."""
import pathlib

import pytest

from lokf import load_bundle

BUNDLE = pathlib.Path(__file__).parent.parent / "examples" / "acme-knowledge"


@pytest.fixture(scope="module")
def bundle():
    return load_bundle(BUNDLE)


def test_loads_eight_concepts_skipping_reserved(bundle):
    assert len(bundle.concepts) == 8
    assert sorted(c.type for c in bundle.concepts) == [
        "AttestedComputation", "Dataset", "GlossaryTerm", "Metric", "Playbook",
        "Reference", "Service", "Table",
    ]


def test_bundle_meta(bundle):
    assert bundle.base_iri == "https://acme.example/knowledge/"
    assert bundle.meta["lokf_version"] == "0.2"


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
    assert len(g) == 153  # examples/acme-knowledge.nt

    from rdflib import URIRef

    wau = URIRef("https://acme.example/knowledge/metrics/weekly-active-users")
    preds = {str(p) for p in g.predicates(subject=wau)}
    assert "http://www.w3.org/ns/prov#wasDerivedFrom" in preds
    assert "http://purl.org/dc/terms/requires" in preds


def test_to_jsonld_injects_id_and_context(bundle):
    docs = bundle.to_jsonld()
    assert len(docs) == 8
    for doc in docs:
        assert "@context" in doc
        assert doc["id"].startswith("https://acme.example/knowledge/")


def test_concept_body_and_title(bundle):
    term = bundle.get("glossary/active-user")
    assert term.title == "Active User"
    assert "# Definition" in term.body


# -- relation-target namespace scoping (issue #64) ---------------------------
def _bundle(tmp_path, base_iri="https://ex.org/kb/"):
    (tmp_path / "index.md").write_text(
        f"---\nbase_iri: {base_iri}\ntitle: KB\n---\n" if base_iri
        else "---\ntitle: KB\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "a.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: A\ndefinition: d\n---\n\n# A\n", encoding="utf-8"
    )
    return load_bundle(tmp_path)


def test_in_namespace_accepts_relative_refs(tmp_path):
    """A relative ref is always the bundle's own: resolve() mints it under base_iri."""
    b = _bundle(tmp_path)
    assert b.in_namespace("a")
    assert b.in_namespace("/glossary/a.md")


def test_in_namespace_accepts_absolute_iris_under_base_iri(tmp_path):
    b = _bundle(tmp_path)
    assert b.in_namespace("https://ex.org/kb/a")


def test_in_namespace_rejects_external_iris(tmp_path):
    """An off-site resource is not something the bundle can vouch for."""
    b = _bundle(tmp_path)
    assert not b.in_namespace("https://elsewhere.example/doc")
    assert not b.in_namespace("urn:isbn:123")
    # a sibling namespace that merely shares a prefix boundary
    assert not b.in_namespace("https://ex.org/other/a")


def test_in_namespace_without_a_base_iri_checks_nothing_absolute(tmp_path):
    """base_iri defaults to "", and "".startswith() matches everything - so an
    absent base_iri must not turn every external IRI into a dangling ref."""
    b = _bundle(tmp_path, base_iri="")
    assert not b.in_namespace("https://elsewhere.example/doc")
    assert b.in_namespace("a")


def test_dangling_refs_reports_concept_slot_and_target(tmp_path):
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "t.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        "isPartOf: [https://ex.org/kb/ghost]\n---\n\n# T\n",
        encoding="utf-8",
    )
    assert load_bundle(tmp_path).dangling_refs() == [
        ("t", "isPartOf", "https://ex.org/kb/ghost")
    ]


def test_dangling_refs_is_empty_for_the_reference_bundle():
    assert load_bundle(BUNDLE).dangling_refs() == []
