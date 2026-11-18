"""Conformance checks for the data shared by all static navigation routes."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from lokf.export import to_cytoscape
from lokf.model import Bundle, Concept, load_bundle
from lokf.schema import Vocabulary, vocabulary
from lokf.views import compile_views


ROOT = Path(__file__).resolve().parents[1]
ACME = ROOT / "examples/acme-knowledge"


def test_packaged_validator_matches_linkml_manifest_schema():
    from linkml.generators.jsonschemagen import JsonSchemaGenerator

    source = ROOT / "web/public/schemas/lokf-views-v1.yaml"
    packaged = ROOT / "src/lokf/data/lokf-views-v1.schema.json"
    generated = JsonSchemaGenerator(str(source), not_closed=False, include_null=False).serialize()
    assert json.loads(packaged.read_text()) == json.loads(generated)


def view(cls, display=None, sections=None):
    return {
        "id": "entry", "title": "Read", "description": "Choose a starting point.",
        "roots": {"type": cls}, "index": display or {"layout": "list"}, "sections": sections or [],
    }


def section(steps, display=None):
    return {"id": "results", "title": "Connected records", "path": steps, "display": display or {"layout": "list"}}


def compile_manifest(tmp_path, definition, bundle=None, vocab=None):
    path = tmp_path / "lokf.views.yaml"
    path.write_text(yaml.safe_dump({"version": "1", "views": [definition]}))
    bundle = bundle or load_bundle(ACME)
    vocab = vocab or vocabulary()
    return compile_views(path, bundle, vocab, to_cytoscape(bundle, vocab))


def test_two_hops_mix_direction_and_resolve_predicate_spellings(tmp_path):
    definition = view("Dataset", sections=[section([
        {"out": "http://schema.org/hasPart", "type": "Table"},
        {"in": "prov:wasDerivedFrom", "type": "Metric"},
    ])])
    plan = compile_manifest(tmp_path, definition)
    root, = plan["views"][0]["roots"]
    assert root["id"] == "datasets/events"
    row, = root["sections"]["results"]
    assert row == {"id": "metrics/weekly-active-users", "witness": [
        {"id": "tables/user-events", "predicate": "schema:hasPart", "direction": "out", "reified": False},
        {"id": "metrics/weekly-active-users", "predicate": "prov:wasDerivedFrom", "direction": "in", "reified": False},
    ]}
    assert plan["records"][row["id"]]["title"] == "Weekly Active Users"


def test_witness_is_reproducible_across_diamonds_cycles_and_reified_edges(tmp_path):
    def record(id_, **data):
        return Concept(tmp_path / f"{id_}.md", {"type": "Document", **data}, id_)

    bundle = Bundle(tmp_path, {"base_iri": "https://kb.example/"}, [
        record("root", hasPart=["b", "a", "https://external.example/record"]),
        record("a", relations=[{"predicate": "relatedTo", "target": "urn:example:leaf"}], relatedTo=["root"]),
        record("b", relatedTo=["urn:example:leaf"]), record("leaf", id="urn:example:leaf"),
    ])
    # The graph follows the explicit IRI even though the static route is /leaf.
    definition = view("Document", sections=[section([{"out": "hasPart"}, {"out": "relatedTo"}])])
    definition["roots"]["concept"] = "root"
    plan = compile_manifest(tmp_path, definition, bundle)
    row, = plan["views"][0]["roots"][0]["sections"]["results"]
    assert row["id"] == "leaf"
    assert [hop["id"] for hop in row["witness"]] == ["a", "leaf"]
    assert row["witness"][1]["reified"] is True
    reversed_bundle = Bundle(bundle.root, bundle.meta, list(reversed(bundle.concepts)))
    assert compile_manifest(tmp_path, definition, reversed_bundle) == plan


def test_timeline_groups_by_authored_day_and_retains_undated(tmp_path):
    def record(id_, title, created=None):
        return Concept(tmp_path / f"{id_}.md", {"type": "Document", "title": title, "created": created}, id_)

    bundle = Bundle(tmp_path, {}, [
        record("later", "Later", "2025-01-02T00:02:00+14:00"),
        record("older2", "B", "2025-01-01T23:59:00-07:00"),
        record("older1", "A", "2025-01-01"), record("missing", "Unknown"), record("bad", "Typo", "2025-02-30"),
    ])
    definition = view("Document", {"layout": "timeline", "date": "created", "date_label": "Published"})
    plan = compile_manifest(tmp_path, definition, bundle)
    assert [row["id"] for row in plan["views"][0]["roots"]] == ["later", "older1", "older2", "bad", "missing"]
    assert plan["records"]["later"]["dates"]["created"] == "2025-01-02"
    assert plan["records"]["bad"]["dates"]["created"] is None
    assert any("bad.created: malformed date" in d for d in plan["diagnostics"])
    definition["index"]["direction"] = "asc"
    plan = compile_manifest(tmp_path, definition, bundle)
    assert [row["id"] for row in plan["views"][0]["roots"]] == ["older1", "older2", "later", "bad", "missing"]


def test_quoted_and_yaml_timestamp_keep_publisher_calendar_day(tmp_path):
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "index.md").write_text("---\nbase_iri: https://example.org/\n---\n")
    for name, timestamp in [("quoted", '"2025-01-02T00:02:00+14:00"'), ("native", "2025-01-02T00:02:00+14:00")]:
        (root / f"{name}.md").write_text(f"---\ntype: Document\ncreated: {timestamp}\n---\n")
    definition = view("Document", {"layout": "timeline", "date": "created", "date_label": "Published"})
    plan = compile_manifest(tmp_path, definition, load_bundle(root))
    assert plan["records"]["quoted"]["dates"] == plan["records"]["native"]["dates"] == {"created": "2025-01-02"}


def test_empty_class_still_validates_fields_and_missing_explicit_root_fails(tmp_path):
    display = {"layout": "table", "columns": [{"field": "title", "label": "Name"}, {"field": "tags", "label": "Tags"}]}
    bundle = Bundle(tmp_path, {}, [])
    definition = view("Document", display)
    assert compile_manifest(tmp_path, definition, bundle)["views"][0]["roots"] == []
    display["columns"][1]["field"] = "sources"
    with pytest.raises(ValueError, match=r"views\[0\].index.*'sources'.*scalar"):
        compile_manifest(tmp_path, definition, bundle)
    definition["index"] = {"layout": "list"}
    definition["roots"]["concept"] = "missing"
    with pytest.raises(ValueError, match="missing.*does not select"):
        compile_manifest(tmp_path, definition, bundle)


def test_section_timeline_uses_root_publication_date_without_redating_members(tmp_path):
    vocab = Vocabulary({
        "classes": {"Concept": {}, "Issue": {"is_a": "Concept", "slots": ["published", "mentions"]},
                    "Development": {"is_a": "Concept"}},
        "slots": {"published": {"range": "date"}, "mentions": {
            "range": "Concept", "multivalued": True, "slot_uri": "urn:example:mentions",
        }},
    })
    bundle = Bundle(tmp_path, {}, [
        Concept(tmp_path / "i.md", {"type": "Issue", "published": "2025-12-11", "mentions": ["z", "a"]}, "i"),
        Concept(tmp_path / "z.md", {"type": "Development", "title": "Zulu"}, "z"),
        Concept(tmp_path / "a.md", {"type": "Development", "title": "Alpha"}, "a"),
    ])
    display = {"layout": "timeline", "date": "published", "date_from": "root", "date_label": "Reported"}
    definition = view("Issue", sections=[section([{"out": "mentions", "type": "Development"}], display)])
    plan = compile_manifest(tmp_path, definition, bundle, vocab)
    assert plan["views"][0]["sections"][0]["display"] == display
    assert plan["views"][0]["roots"][0]["sections"]["results"] == [{"id": "a"}, {"id": "z"}]
    assert plan["records"]["i"]["dates"] == {"published": "2025-12-11"}
    assert plan["records"]["a"]["dates"] == plan["records"]["z"]["dates"] == {}
    del display["date_from"]
    with pytest.raises(ValueError, match="date or datetime field of Development"):
        compile_manifest(tmp_path, definition, bundle, vocab)


@pytest.mark.parametrize(("update", "message"), [
    ({"sections": [section([{"in": "typo"}])]}, "unknown projected relation 'typo'"),
    ({"sections": [section([{"in": "hasPart", "out": "hasPart"}])]}, "one"),
    ({"sections": [section([{"in": "hasPart", "type": "Source"}])]}, "unknown concept class 'Source'"),
    ({"sections": [section([{"in": "hasPart"}] * 5)]}, "too long"),
    ({"index": {"layout": "list", "embed": ["missing"]}}, "unknown section"),
    ({"index": {"layout": "table"}}, "title column"),
    ({"index": {"layout": "list", "date": "created"}}, "does not support date"),
    ({"index": {"layout": "timeline", "date": "title", "date_label": "Published"}}, "single-valued date"),
    ({"index": {"layout": "timeline", "date": "created", "date_label": "By day", "date_from": "root"}},
     "does not support date_from"),
    ({"sections": [section([{"out": "hasPart"}], {"layout": "list", "date_from": "root"})]},
     "does not support date_from"),
    ({"sections": [section([{"out": "hasPart"}], {"layout": "timeline", "date_from": "unknown"})]},
     "'root' was expected"),
    ({"index": {"layout": "timeline", "date": "created", "date_label": "Created",
                "family_by": {"out": "isPartOf"}}}, "does not support family_by"),
    ({"index": {"layout": "table", "columns": [{"field": "title", "label": "Name"}],
                "family_by": {"out": "isPartOf"}}}, "does not support family_by"),
    ({"sections": [section([{"out": "hasPart"}], {"layout": "timeline", "date": "created",
                  "date_label": "Created", "order_by": {"out": "derivedFrom"}})]}, "does not support order_by"),
    ({"unknown": "property"}, "Additional properties"),
])
def test_rejects_invalid_declarations(tmp_path, update, message):
    with pytest.raises(ValueError, match=message):
        compile_manifest(tmp_path, {**view("Document"), **update})


def test_manifest_rejects_duplicate_keys(tmp_path):
    path = tmp_path / "lokf.views.yaml"
    path.write_text('version: "1"\nversion: "1"\nviews: []\n')
    with pytest.raises(ValueError, match="duplicate key"):
        compile_views(path, Bundle(tmp_path, {}, []), vocabulary(), {"edges": []})


def test_ambiguous_slot_and_enum_names_need_explicit_predicate(tmp_path):
    vocab = Vocabulary({
        "classes": {"Concept": {"slots": ["points"]}},
        "slots": {"points": {"range": "Concept", "multivalued": True, "slot_uri": "https://example.org/one"}},
        "enums": {"RelationType": {"permissible_values": {"points": {"meaning": "https://example.org/two"}}}},
    })
    definition = view("Concept", sections=[section([{"out": "points"}])])
    with pytest.raises(ValueError, match="ambiguous relation"):
        compile_manifest(tmp_path, definition, Bundle(tmp_path, {}, []), vocab)
    definition["sections"][0]["path"] = [{"out": "https://example.org/one"}]
    assert compile_manifest(tmp_path, definition, Bundle(tmp_path, {}, []), vocab)["views"][0]["roots"] == []


def graph_bundle(tmp_path, records):
    return Bundle(tmp_path, {"base_iri": "https://kb.example/"}, [
        Concept(tmp_path / f"{id_}.md", {"type": "Document", **data}, id_)
        for id_, data in records.items()
    ])


def test_untyped_section_reads_core_fields_from_a_record_with_an_unknown_type(tmp_path):
    bundle = graph_bundle(tmp_path, {
        "start": {"hasPart": ["child"]},
        "child": {"type": "FieldNote", "description": "Recorded description"},
    })
    parts = section([{"out": "hasPart"}], {"layout": "table", "columns": [
        {"field": "title", "label": "Title"}, {"field": "description", "label": "Description"},
    ]})
    plan = compile_manifest(tmp_path, view("Document", sections=[parts]), bundle)
    assert plan["records"]["child"]["fields"]["description"] == "Recorded description"


def test_relation_columns_project_from_each_row_and_keep_links_local_to_its_display(tmp_path):
    bundle = graph_bundle(tmp_path, {
        "root": {"tags": ["vintage"], "hasPart": ["stage", "empty"], "relatedTo": ["root"]},
        "stage": {"type": "Table", "title": "B", "relatedTo": [
            "urn:z", "urn:a", "urn:a", "empty", "https://external.example/metric",
        ], "relations": [{"predicate": "relatedTo", "target": "reified-only"}]},
        "empty": {"type": "Table", "title": "A"},
        "first-by-id": {"type": "Metric", "title": "Tied", "id": "urn:z"},
        "last-by-id": {"type": "Metric", "title": "Tied", "id": "urn:a"},
        "reified-only": {"type": "Metric", "title": "Alpha"},
    })
    title = {"field": "title", "label": "Name"}
    index = {"layout": "table", "columns": [
        title, {"field": "tags", "label": "Tags"},
        {"relation": {"out": "schema:hasPart", "type": "Table"}, "label": "Stages"},
        {"relation": {"out": "relatedTo"}, "label": "Related"},
    ]}
    steps = [{"out": "hasPart", "type": "Table"}]
    metrics = section(steps, {"layout": "table", "columns": [
        title, {"relation": {"out": "relatedTo", "type": "Metric"}, "label": "Metrics"},
    ]})
    owners = {**section(steps, {"layout": "table", "columns": [
        title, {"relation": {"in": "http://schema.org/hasPart"}, "label": "Owners"},
    ]}), "id": "owners"}
    plan = compile_manifest(tmp_path, view("Document", index, [metrics, owners]), bundle)
    root, = plan["views"][0]["roots"]
    assert root["links"] == {"2": ["empty", "stage"], "3": ["root"]}
    assert plan["records"]["root"]["fields"] == {"tags": ["vintage"]}
    assert root["sections"]["results"] == [
        {"id": "empty", "links": {"1": []}},
        {"id": "stage", "links": {"1": ["reified-only", "last-by-id", "first-by-id"]}},
    ]
    assert root["sections"]["owners"] == [
        {"id": "empty", "links": {"1": ["root"]}},
        {"id": "stage", "links": {"1": ["root"]}},
    ]
    assert set(plan["records"]) == {c.concept_id for c in bundle.concepts}
    assert plan["records"]["reified-only"]["title"] == "Alpha"
    reversed_bundle = Bundle(bundle.root, bundle.meta, list(reversed(bundle.concepts)))
    assert compile_manifest(tmp_path, view("Document", index, [metrics, owners]), reversed_bundle) == plan


@pytest.mark.parametrize(("column", "message"), [
    ({"relation": {"out": "missing"}}, r"columns\[1\].relation.out: unknown projected relation"),
    ({"relation": {"in": "hasPart", "type": "Typo"}}, r"columns\[1\].relation.type: unknown concept class"),
    ({"relation": {"out": "hasPart", "in": "hasPart"}}, r"columns\[1\].relation: a step needs exactly one direction"),
    ({"relation": {}}, r"columns\[1\].relation: a step needs exactly one direction"),
    ({"field": "title", "relation": {"out": "hasPart"}}, r"columns\[1\]: a column needs exactly one"),
    ({}, r"columns\[1\]: a column needs exactly one"),
])
def test_relation_columns_validate_without_rows(tmp_path, column, message):
    display = {"layout": "table", "columns": [{"field": "title", "label": "Name"}, {"label": "Links", **column}]}
    definition = view("Document", sections=[section([{"out": "hasPart"}], display)])
    with pytest.raises(ValueError, match=message):
        compile_manifest(tmp_path, definition, graph_bundle(tmp_path, {}))


def test_relation_column_cannot_replace_title_at_start_of_table(tmp_path):
    display = {"layout": "table", "columns": [{"relation": {"out": "hasPart"}, "label": "Links"}]}
    with pytest.raises(ValueError, match=r"index.columns.*title column"):
        compile_manifest(tmp_path, view("Document", display), graph_bundle(tmp_path, {}))


def test_family_index_includes_every_root_and_groups_transitive_members_once(tmp_path):
    # Use an incoming step, with a shared descendant reached by two routes
    # in the first family, a second parent family, and an out-of-scope parent.
    bundle = graph_bundle(tmp_path, {
        "family-z": {"title": "A family", "hasPart": ["branch-b", "branch-a"]},
        "branch-a": {"hasPart": ["deep"]}, "branch-b": {"hasPart": ["deep"]},
        "deep": {"title": "A deep leaf"}, "family-a": {"title": "B family", "hasPart": ["deep"]},
        "singleton": {}, "other": {"type": "Table", "hasPart": ["singleton"]},
    })
    definition = view("Document", {"layout": "list", "family_by": {"in": "hasPart", "type": "Document"}})
    plan = compile_manifest(tmp_path, definition, bundle)
    index = plan["views"][0]
    assert index["families"] == [
        {"id": "family-z", "members": ["deep", "branch-a", "branch-b"]},
        {"id": "family-a", "members": ["deep"]}, {"id": "singleton", "members": []},
    ]
    assert len(index["roots"]) == 6
    reversed_bundle = Bundle(bundle.root, bundle.meta, list(reversed(bundle.concepts)))
    assert compile_manifest(tmp_path, definition, reversed_bundle) == plan
    definition["roots"]["concept"] = "deep"
    index = compile_manifest(tmp_path, definition, bundle)["views"][0]
    assert index["families"] == [{"id": "deep", "members": []}]


@pytest.mark.parametrize("direction", ["in", "out"])
def test_explicit_stage_order_respects_dependencies_and_breaks_ties_by_title_and_iri(tmp_path, direction):
    inputs = {"raw": [], "typed": ["raw"], "reviewed": ["typed", "qc"],
              "encoded": ["reviewed"], "qc": [], "free-b": [], "free-a": ["outside"]}
    records = {
        "root": {"hasPart": list(inputs)}, "outside": {},
        "raw": {"title": "B"}, "typed": {"title": "A"}, "reviewed": {"title": "A"},
        "encoded": {"title": "A"}, "qc": {"title": "Y"}, "free-b": {"title": "Z"}, "free-a": {"title": "Z"},
    }
    for stage, dependencies in inputs.items():
        for dependency in dependencies:
            source, target = (stage, dependency) if direction == "out" else (dependency, stage)
            records[source].setdefault("derivedFrom", []).append(target)
    display = {"layout": "table", "columns": [{"field": "title", "label": "Stage"}],
               "order_by": {direction: "derivedFrom", "type": "Document"}}
    definition = view("Document", sections=[section([{"out": "hasPart"}], display)])
    definition["roots"]["concept"] = "root"
    bundle = graph_bundle(tmp_path, records)
    plan = compile_manifest(tmp_path, definition, bundle)
    rows = plan["views"][0]["roots"][0]["sections"]["results"]
    assert [row["id"] for row in rows] == ["raw", "typed", "qc", "reviewed", "encoded", "free-a", "free-b"]
    reversed_bundle = Bundle(bundle.root, bundle.meta, list(reversed(bundle.concepts)))
    assert compile_manifest(tmp_path, definition, reversed_bundle) == plan


@pytest.mark.parametrize("self_loop", [False, True])
def test_cycles_identify_selector_scope_and_involved_records(tmp_path, self_loop):
    bundle = graph_bundle(tmp_path, {
        "root": {"hasPart": ["a", "b"]}, "a": {"isPartOf": ["a" if self_loop else "b"]},
        "b": {"isPartOf": ["a"]},
    })
    step = {"out": "isPartOf"}
    family = view("Document", {"layout": "list", "family_by": step})
    with pytest.raises(ValueError, match=r"views\[0\].index.family_by: cycle.*a"):
        compile_manifest(tmp_path, family, bundle)
    definition = view("Document", sections=[section([{"out": "hasPart"}], {"layout": "list", "order_by": step})])
    with pytest.raises(ValueError, match=r"sections\[0\].display.order_by \(root root\): cycle.*a"):
        compile_manifest(tmp_path, definition, bundle)


def test_ordering_coverage_distinguishes_chain_fork_and_unlinked_for_each_root(tmp_path):
    bundle = graph_bundle(tmp_path, {
        "chain": {"type": "Table", "hasPart": ["a", "b", "c"]},
        "fork": {"type": "Table", "hasPart": ["a", "b", "d"]},
        "no-edges": {"type": "Table", "hasPart": ["c", "d"]},
        "one": {"type": "Table", "hasPart": ["b"]}, "zero": {"type": "Table"},
        "a": {}, "b": {"derivedFrom": ["a"]}, "c": {"derivedFrom": ["b"]}, "d": {"derivedFrom": ["a"]},
    })
    steps = [{"out": "hasPart"}]
    ordered = section(steps, {"layout": "list", "order_by": {"out": "derivedFrom"}})
    unconfigured = {**section(steps), "id": "alphabetical"}
    definition = view("Table", sections=[ordered, unconfigured])
    plan = compile_manifest(tmp_path, definition, bundle)
    roots = {root["id"]: root.get("ordering") for root in plan["views"][0]["roots"]}
    assert roots == {
        "chain": {"results": "complete"}, "fork": {"results": "partial"},
        "no-edges": {"results": "unlinked"}, "one": None, "zero": None,
    }


def test_family_and_order_validate_relation_even_with_no_matches(tmp_path):
    bundle = graph_bundle(tmp_path, {})
    definition = view("Document", {"layout": "list", "family_by": {"out": "isPartOf"}})
    assert compile_manifest(tmp_path, definition, bundle)["views"][0]["families"] == []
    definition["index"]["family_by"] = {"out": "typo"}
    with pytest.raises(ValueError, match="index.family_by.out: unknown projected relation"):
        compile_manifest(tmp_path, definition, bundle)
    definition = view("Document", sections=[
        section([{"out": "hasPart"}], {"layout": "list", "order_by": {"out": "typo"}}),
    ])
    with pytest.raises(ValueError, match="display.order_by.out: unknown projected relation"):
        compile_manifest(tmp_path, definition, bundle)
