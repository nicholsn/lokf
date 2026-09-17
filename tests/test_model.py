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


def test_duplicate_iris_names_every_file_claiming_one_iri(tmp_path):
    """A conflict copy carries its original's explicit `id`; an explicit `id`
    can also equal another file's path-derived one. Both are one IRI twice."""
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    a = "---\nid: https://ex.org/kb/a\ntype: GlossaryTerm\ntitle: A\n---\n"
    (tmp_path / "a.md").write_text(a, encoding="utf-8")
    (tmp_path / "a (conflicted copy).md").write_text(a, encoding="utf-8")
    (tmp_path / "b.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: B\n---\n", encoding="utf-8"
    )
    (tmp_path / "c.md").write_text(
        "---\nid: https://ex.org/kb/b\ntype: GlossaryTerm\ntitle: C\n---\n",
        encoding="utf-8",
    )
    # Files in the bundle's sorted path order: a space sorts before a dot.
    assert load_bundle(tmp_path).duplicate_iris() == [
        ("https://ex.org/kb/a", ["a (conflicted copy)", "a"]),
        ("https://ex.org/kb/b", ["b", "c"]),
    ]


def test_duplicate_iris_is_empty_for_the_reference_bundle():
    assert load_bundle(BUNDLE).duplicate_iris() == []
