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


def test_manifest_emits_the_full_vocabulary_with_descriptions(vocab):
    m = vocab.manifest()
    assert m["schema_version"]

    # Every schema enum is present - not a hand-picked subset (regression
    # guard: manifest() must derive its enum list from the schema itself).
    assert set(m["enums"]) == set(vocab._schema.get("enums", {}))
    assert "ParameterType" in m["enums"] and m["enums"]["ParameterType"]
    assert "FieldType" in m["enums"] and m["enums"]["FieldType"]

    # Slots carry the schema's own field descriptions (the field reference).
    slots = {s["name"]: s for s in m["slots"] if "class" not in s}
    assert slots["base_iri"]["description"]
    assert slots["genre"]["description"]

    # The type vocabulary is present, and at least some classes are described.
    classes = {c["name"]: c for c in m["classes"]}
    assert "Metric" in classes and "Dataset" in classes
    assert any(c.get("description") for c in m["classes"])

    # Value enums carry their permissible values, with descriptions.
    genres = {g["value"]: g for g in m["enums"]["DiataxisMode"]}
    assert {"tutorial", "how-to", "reference", "explanation"} <= set(genres)
    assert genres["how-to"].get("description")
    statuses = {s["value"] for s in m["enums"]["ConceptStatus"]}
    assert {"draft", "stable", "deprecated"} <= statuses
    relations = {r["value"] for r in m["enums"]["RelationType"]}
    assert "dependsOn" in relations


def test_manifest_is_json_serializable(vocab):
    import json

    json.dumps(vocab.manifest())  # must not raise (no sets, frozensets, etc.)


def test_class_docs_covers_embedded_object_classes_too(vocab):
    classes = {c["name"]: c for c in vocab.class_docs()}

    # Concept/Agent descendants are the `type:` vocabulary.
    assert classes["Metric"]["is_type_value"] is True
    assert classes["Dataset"]["is_type_value"] is True

    # Embedded object shapes are documented too, just flagged as not valid
    # `type:` values - they were silently dropped before this fix.
    assert classes["Parameter"]["is_type_value"] is False
    assert classes["Source"]["is_type_value"] is False
    assert classes["Parameter"]["description"]

    # Person/Organization reach Concept only via `mixins: [Concept]`, not a
    # pure `is_a` chain - confirms _descends_from honors mixins.
    assert classes["Person"]["is_type_value"] is True


def test_slot_docs_surfaces_class_local_overrides(vocab):
    rows = vocab.slot_docs()
    generic_type = next(r for r in rows if r["name"] == "type" and "class" not in r)
    parameter_type = next(
        r for r in rows if r["name"] == "type" and r.get("class") == "Parameter"
    )
    assert parameter_type["description"] != generic_type["description"]


def test_enum_values_matches_relation_types_curie_convention(vocab):
    # enum_values("RelationType") must agree with the pre-existing
    # relation_types computation for the same value (both fall back to a
    # minted lokf:<name> term when no explicit `meaning` is given).
    rows = {r["value"]: r for r in vocab.enum_values("RelationType")}
    for name, rel in vocab.relation_types.items():
        assert rows[name]["curie"] == rel.curie
        assert rows[name]["uri"] == rel.uri
# -- excerpt / reference-validator wiring (Source) ---------------------------
def test_source_declares_excerpt_slot():
    schema = load_schema()
    source = schema["classes"]["Source"]
    assert "excerpt" in source["slots"]
    # Optional: a Source may cite a resource without quoting it verbatim.
    assert "required" not in source.get("slot_usage", {}).get("excerpt", {})
    # The 0.8.0 name is gone from the schema, not aliased into it: a bundle
    # still writing it fails validation and says so.
    assert "supporting_text" not in schema["slots"]
    assert "supporting_text" in schema["slots"]["excerpt"]["aliases"]


def test_excerpt_slot_implements_linkml_excerpt(vocab):
    slot = load_schema()["slots"]["excerpt"]
    assert slot["range"] == "string"
    assert slot["implements"] == ["linkml:excerpt"]
    # Named as proposed for OKF §5.1 (knowledge-catalog#438); LOKF's own
    # predicate until OKF adopts it, so it sits in lokf_semantic, not okf_v02.
    assert slot["slot_uri"] == "lokf:excerpt"
    assert slot["in_subset"] == ["lokf_semantic"]
    # linkml_reference_validator's field_detection matches this legacy URI
    # (canonical is oa:exact) to find excerpt fields for validation.
    assert vocab.expand("linkml:excerpt") == "https://w3id.org/linkml/excerpt"


def test_source_resource_implements_dcterms_source(vocab):
    resource_usage = load_schema()["classes"]["Source"]["slot_usage"]["resource"]
    assert resource_usage["implements"] == ["dcterms:source"]
    assert resource_usage["required"] is True
    # linkml_reference_validator pairs this with the excerpt field above to
    # fetch `resource` and confirm `excerpt` actually appears in it.
    assert vocab.expand("dcterms:source") == "http://purl.org/dc/terms/source"


def test_revision_is_lokfs_own_event_field_until_okf_adopts_it():
    """`revision` pins which state of the resource a `generated` or `verified`
    event refers to. Proposed for OKF as knowledge-catalog#437, so it lives
    in lokf_semantic under LOKF's own predicate, on both event classes, and
    is never required."""
    schema = load_schema()
    slot = schema["slots"]["revision"]
    assert slot["range"] == "string"
    assert slot["slot_uri"] == "lokf:revision"
    assert slot["in_subset"] == ["lokf_semantic"]
    assert "required" not in slot
    for cls in ("Generation", "Verification"):
        assert "revision" in schema["classes"][cls]["slots"], cls


# -- OKF §5 timestamps -------------------------------------------------------
def test_datetime_slots_match_the_parser_shorthand_set():
    """OKF types every timestamp as a datetime; LOKF reads a bare date under
    those keys as midnight UTC. The parser's key set must be the schema's, or
    a slot gains the datetime range and loses the shorthand silently."""
    from lokf.parse import DATETIME_SLOTS

    schema = load_schema()
    datetime_slots = {
        name for name, slot in schema["slots"].items()
        if (slot or {}).get("range") == "datetime"
    }
    assert datetime_slots == set(DATETIME_SLOTS)
    # No slot is left on the narrower `date` range OKF never uses.
    assert not [n for n, s in schema["slots"].items() if (s or {}).get("range") == "date"]


# -- vocab manifest carries the constraints, not just the glosses ------------
def test_manifest_reports_patterns_required_and_slot_usage(vocab):
    """A client that cannot run `lokf validate` (the MCP `get_vocabulary`
    route) must see every constraint lokf.schema.json enforces, and each
    class's narrowing of a slot - or it writes values the validator rejects."""
    schema = load_schema()
    m = vocab.manifest()
    slots = {s["name"]: s for s in m["slots"] if "class" not in s}
    for name, slot in schema["slots"].items():
        slot = slot or {}
        if slot.get("pattern"):
            assert slots[name]["pattern"] == slot["pattern"], name
        if slot.get("required"):
            assert slots[name]["required"] is True, name

    classes = {c["name"]: c for c in m["classes"]}
    for name, cls in schema["classes"].items():
        for slot_name, override in ((cls or {}).get("slot_usage") or {}).items():
            if override and override.get("recommended"):
                assert classes[name]["slot_usage"][slot_name]["recommended"] is True
    # Source narrows the Agent-list `author` to one patterned string; the
    # top-level row alone would have a client write a list of objects.
    author = classes["Source"]["slot_usage"]["author"]
    assert author["range"] == "string"
    assert author["multivalued"] is False
    assert author["pattern"] == schema["classes"]["Source"]["slot_usage"]["author"]["pattern"]
    # Loader mechanics stay out of the contract.
    assert "inlined_as_list" not in author and "implements" not in classes["Source"]["slot_usage"]["resource"]


# Slot descriptions are canonical, verbatim glosses surfaced one-per-row by
# consumers such as gen-doc and the Enforcer lookup. Keep rationale, mappings,
# and loader mechanics in `comments:`/`notes:` instead.
#
# 400 chars is the shared soft cap for a readable lookup row; classes and enums
# are exempt because their descriptions summarize whole types or vocabularies.
# Raise the cap only when a field genuinely cannot be glossed shorter,
# and hopefully downstream consumers don't mind the occasional long one.
SLOT_DESCRIPTION_MAX = 400


def test_slot_descriptions_stay_a_gloss_not_an_essay(vocab):
    too_long = {
        s["name"]: len(s["description"])
        for s in vocab.manifest()["slots"]
        if len(s.get("description", "")) > SLOT_DESCRIPTION_MAX
    }
    assert not too_long, (
        f"slot descriptions over {SLOT_DESCRIPTION_MAX} chars: {too_long}. "
        "A description is the canonical gloss; move rationale, mapping choices, "
        "and loader mechanics into the slot's `comments:`/`notes:`."
    )


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
        usage_window={"from": "2026-06-01T00:00:00Z", "to": "2026-06-30T00:00:00Z"},
    )
    assert isinstance(m.usage_window, UsageWindow)
    assert str(m.usage_window.from_) == "2026-06-01T00:00:00+00:00"
    assert str(m.usage_window.to) == "2026-06-30T00:00:00+00:00"


# -- PR #69: recommended fields, slot patterns, HttpMethod enum ----------
# -- recommended fields + the vocabulary manifest ----------------------------
def test_recommended_fields_are_declared_per_type():
    schema = load_schema()

    def recommended(cls):
        usage = schema["classes"][cls].get("slot_usage") or {}
        return {s for s, u in usage.items() if (u or {}).get("recommended")}

    assert recommended("Metric") == {"unit", "formula", "measures"}
    assert recommended("GlossaryTerm") == {"definition"}
    # http_method is excluded on purpose: its own description says "if
    # applicable", and a GraphQL or gRPC Service has no single verb.
    assert recommended("Service") == {"endpoint", "documentation"}
    assert "http_method" not in recommended("Service")


def test_dataset_recommends_nothing_so_table_inherits_nothing():
    # Table is_a Dataset, so anything recommended on Dataset propagates to it.
    # `distribution` is meaningless for a warehouse table, and neither the SPEC
    # nor the enforcer plugin treats either field as a SHOULD.
    schema = load_schema()
    assert schema["classes"]["Table"]["is_a"] == "Dataset"
    assert not (schema["classes"]["Dataset"].get("slot_usage") or {})


# -- `base_iri` pattern (SPEC §5: absolute http(s), `/`- or `#`-terminated) ---
def test_base_iri_slot_has_absolute_terminated_pattern():
    import re

    pattern = load_schema()["slots"]["base_iri"]["pattern"]
    good = [
        "https://acme.example/knowledge/",
        "http://ex.org/kb/",
        "https://ex.org/ns#",  # hash namespaces are valid, per registry.add()
    ]
    bad = [
        "https://acme.example/knowledge",  # unterminated: ids would mint glued
        "acme.example/knowledge/",  # not absolute
        "ftp://ex.org/kb/",  # not http(s)
        "https://ex.org/a b/",  # whitespace
    ]
    for value in good:
        assert re.fullmatch(pattern, value), f"{value!r} should match {pattern!r}"
    for value in bad:
        assert not re.fullmatch(pattern, value), f"{value!r} should not match {pattern!r}"


def test_base_iri_pattern_admits_every_registrable_base_iri():
    # The schema pattern must not be narrower than the rule registry.add()
    # enforces, or a bundle that routes today would stop validating.
    import re

    from lokf.registry import Registry, RepoEntry

    pattern = load_schema()["slots"]["base_iri"]["pattern"]
    for value in ["https://acme.example/knowledge/", "https://ex.org/ns#"]:
        Registry(path=pathlib.Path("lokf-registry.yaml")).add(RepoEntry(base_iri=value))
        assert re.fullmatch(pattern, value), f"registry accepts {value!r}, schema rejects it"


# -- `by` actor-string pattern (OKF §7: human:<id> | process:<id> | <producer>/<version>) --
def test_by_slot_has_actor_string_pattern():
    import re

    pattern = load_schema()["slots"]["by"]["pattern"]
    good = [
        "human:jsmith@acme",
        "process:metrics-nightly",
        "reference_agent/gemini-2.5-pro",
    ]
    bad = ["John Smith", "human:", "has space/version", "no-scheme-no-slash"]
    for value in good:
        assert re.fullmatch(pattern, value), f"{value!r} should match {pattern!r}"
    for value in bad:
        assert not re.fullmatch(pattern, value), f"{value!r} should not match {pattern!r}"


def test_source_author_admits_any_prefixed_actor():
    # Source.author carries an actor string but is a distinct slot from `by`
    # (the global `author` ranges over Agent, so nothing is inherited). It is
    # deliberately looser: sources are commonly credited to a team, which the
    # §7 provenance trio has no form for.
    import re

    schema = load_schema()
    pattern = schema["classes"]["Source"]["slot_usage"]["author"]["pattern"]
    good = ["team:analytics", "human:jsmith@acme", "process:crawler", "ga4-docs/v2"]
    bad = ["Jordan Smith", "team:", "has space/version", "noprefix"]
    for value in good:
        assert re.fullmatch(pattern, value), f"{value!r} should match {pattern!r}"
    for value in bad:
        assert not re.fullmatch(pattern, value), f"{value!r} should not match {pattern!r}"
    # ...and it must stay strictly looser than `by`, never narrower.
    by = schema["slots"]["by"]["pattern"]
    assert re.fullmatch(pattern, "team:analytics")
    assert not re.fullmatch(by, "team:analytics")


# -- `email` pattern and `http_method` enum ----------------------------------
def test_email_slot_has_pattern():
    import re

    pattern = load_schema()["slots"]["email"]["pattern"]
    for value in ["jsmith@acme.example", "a.b+tag@sub.example.co"]:
        assert re.fullmatch(pattern, value), f"{value!r} should match {pattern!r}"
    for value in ["not-an-email", "missing-domain@", "@no-local.com", "no at sign.com"]:
        assert not re.fullmatch(pattern, value), f"{value!r} should not match {pattern!r}"


def test_http_method_is_an_enum_of_iana_verbs():
    schema = load_schema()
    assert schema["slots"]["http_method"]["range"] == "HttpMethod"
    assert set(schema["enums"]["HttpMethod"]["permissible_values"]) == {
        "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS",
    }
