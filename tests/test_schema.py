"""Vocabulary derivation from lokf.yaml."""
import pathlib

import pytest
import yaml

from lokf.schema import load_context, load_schema, vocabulary

ROOT = pathlib.Path(__file__).parent.parent


@pytest.fixture(scope="module")
def vocab():
    return vocabulary()


def test_relation_slots_discovered(vocab):
    # The ten Concept-level typed-relation keys, Metric's `measures`, and
    # Role's `memberOf` / `holder`.
    assert set(vocab.relation_slots) == {
        "isPartOf", "hasPart", "references", "dependsOn", "derivedFrom",
        "about", "sameAs", "relatedTo", "definedBy", "source", "measures",
        "memberOf", "holder",
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


# -- supporting_text / reference-validator wiring (Source) -------------------
def test_source_declares_supporting_text_slot():
    schema = load_schema()
    source = schema["classes"]["Source"]
    assert "supporting_text" in source["slots"]
    # Optional: a Source may cite a resource without quoting it verbatim.
    assert "required" not in source.get("slot_usage", {}).get("supporting_text", {})


def test_supporting_text_slot_implements_linkml_excerpt(vocab):
    slot = load_schema()["slots"]["supporting_text"]
    assert slot["range"] == "string"
    assert slot["implements"] == ["linkml:excerpt"]
    # linkml_reference_validator's field_detection matches this legacy URI
    # (canonical is oa:exact) to find excerpt fields for validation.
    assert vocab.expand("linkml:excerpt") == "https://w3id.org/linkml/excerpt"


def test_source_resource_implements_dcterms_source(vocab):
    resource_usage = load_schema()["classes"]["Source"]["slot_usage"]["resource"]
    assert resource_usage["implements"] == ["dcterms:source"]
    assert resource_usage["required"] is True
    # linkml_reference_validator pairs this with the excerpt field above to
    # fetch `resource` and confirm `supporting_text` actually appears in it.
    assert vocab.expand("dcterms:source") == "http://purl.org/dc/terms/source"


def test_context_has_authoring_aliases():
    ctx = load_context()
    assert ctx["type"] == "@type"
    assert ctx["id"] == "@id"


def test_schema_loads():
    schema = load_schema()
    assert schema["name"] == "lokf" or "lokf" in schema.get("id", "")


def test_subclasses_of_is_inclusive(vocab):
    assert vocab.subclasses_of("Dataset") == {"Dataset", "Table"}


def test_packaged_data_matches_root_files():
    """Drift guard: lokf-build must keep the packaged copies byte-identical."""
    for name in ("lokf.yaml", "lokf.context.jsonld"):
        packaged = ROOT / "src" / "lokf" / "data" / name
        assert packaged.read_bytes() == (ROOT / name).read_bytes(), (
            f"src/lokf/data/{name} is out of sync with the repo-root {name}; "
            "run lokf-build"
        )


def test_load_schema_resolves_root_checkout():
    # Run from inside the repo, the no-arg load resolves the checkout's root
    # lokf.yaml (ancestors-first), matching an explicitly-pathed load.
    assert load_schema() == load_schema(ROOT / "lokf.yaml")


def test_ancestor_schema_wins_over_packaged(tmp_path, monkeypatch):
    # A locally edited lokf.yaml in an ancestor of cwd must beat the copy
    # packaged under lokf/data/ (resolution order: ancestors first).
    doctored = yaml.safe_load((ROOT / "lokf.yaml").read_text(encoding="utf-8"))
    doctored["name"] = "lokf-local-edit"
    (tmp_path / "lokf.yaml").write_text(yaml.safe_dump(doctored), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert load_schema()["name"] == "lokf-local-edit"


def test_datamodel_usage_window_from_keyword():
    """The generated dataclasses accept a raw `from`-keyed usage_window dict.

    `from` is a Python keyword (the field is generated as `from_`), but
    reconstruction from YAML/JSON-LD dicts still carries the authored key —
    the build patch must bridge it (regression: TypeError on the example).
    """
    from lokf.datamodel import Metric, UsageWindow

    m = Metric(
        id="https://acme.example/knowledge/metrics/wau",
        type="Metric",
        usage_window={"from": "2026-06-01", "to": "2026-06-30"},
    )
    assert isinstance(m.usage_window, UsageWindow)
    assert str(m.usage_window.from_) == "2026-06-01"
    assert str(m.usage_window.to) == "2026-06-30"
