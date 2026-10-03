"""`lokf adapt`: a published LinkML vocabulary becomes a domain-schema import.

The fixture vocabulary-with-root.yaml is shaped like biolink-model: a root of
its own with an identifier, an rdf:type slot and a designator, lowercase names
with spaces, names LOKF also defines, and a sibling import. The unit tests take
each move on its own; the end-to-end tests import the copy from a domain
schema and run the bundle through `lokf validate` and `lokf convert`. The
biolink test itself runs only after `just biolink` has fetched the model.
"""
import pathlib

import pytest
import yaml
from typer.testing import CliRunner

from lokf import adapt as A
from lokf.cli import app
from lokf.schema import load_schema

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "domain-schema"
VOCAB = FIXTURES / "vocabulary-with-root.yaml"
LOKF = ROOT / "lokf.yaml"
runner = CliRunner()


def _folded() -> dict:
    schema, _ = A.fold_imports(VOCAB)
    return schema


# --- the moves, one at a time ------------------------------------------------

def test_fold_imports_inlines_the_sibling_and_imports_lokf():
    schema, folded = A.fold_imports(VOCAB)
    assert folded == ["vocabulary-with-root-attributes"]
    assert "has attribute" in schema["slots"]
    assert schema["imports"] == ["linkml:types", "lokf"]


def test_fold_imports_lets_each_schema_win_over_its_own_imports(tmp_path):
    """Root over its import, and that import over what it imports itself:
    the deepest definition must not come out on top."""
    (tmp_path / "deep.yaml").write_text("name: deep\nslots:\n  x: {description: deep}\n  y: {description: deep}\n", encoding="utf-8")
    (tmp_path / "mid.yaml").write_text("name: mid\nimports: [deep]\nslots:\n  x: {description: mid}\n", encoding="utf-8")
    (tmp_path / "top.yaml").write_text("name: top\nimports: [linkml:types, mid]\nslots:\n  y: {description: top}\n", encoding="utf-8")
    schema, folded = A.fold_imports(tmp_path / "top.yaml")
    assert folded == ["deep", "mid"]
    assert schema["slots"]["x"]["description"] == "mid"
    assert schema["slots"]["y"]["description"] == "top"


def test_fold_imports_pins_iris_from_a_differently_prefixed_import(tmp_path):
    (tmp_path / "other.yaml").write_text(
        "name: other\ndefault_prefix: other\nprefixes: {other: https://ex.org/other/}\nslots:\n  z: {}\nclasses:\n  thing: {}\n",
        encoding="utf-8",
    )
    (tmp_path / "top.yaml").write_text(
        "name: top\ndefault_prefix: top\nprefixes: {top: https://ex.org/top/}\nimports: [other]\n", encoding="utf-8"
    )
    schema, _ = A.fold_imports(tmp_path / "top.yaml")
    assert schema["slots"]["z"]["slot_uri"] == "other:z"
    assert schema["classes"]["thing"]["class_uri"] == "other:Thing"
    assert schema["prefixes"] == {"other": "https://ex.org/other/", "top": "https://ex.org/top/"}


def test_shared_names_compares_as_linkml_normalises():
    shared = A.shared_names(_folded(), load_schema(LOKF))
    assert shared["classes"] == ["dataset"]  # LOKF's Dataset
    assert set(shared["slots"]) == {"id", "type", "name", "description", "license"}
    assert shared["types"] == ["unit"]  # LOKF's *slot* unit: one namespace
    lokf_like = {"classes": {"NamedThing": {}}, "slots": {"in_taxon": {}}}
    assert A.shared_names(_folded(), lokf_like) == {"classes": ["named thing"], "slots": ["in taxon"]}
    # across sections only names as written clash: LOKF's own Source class and source slot coexist
    assert A.shared_names({"classes": {"Symbol": {}}, "slots": {"Gene": {}}}, {"slots": {"symbol": {}}, "classes": {"gene": {}}}) == {}
    assert A.shared_names({"types": {"unit": {}}}, {"slots": {"unit": {}}}) == {"types": ["unit"]}


def test_drop_twins_removes_the_identifier_and_rdf_type_and_detaches_their_children():
    schema = _folded()
    dropped, detached = A.drop_twins(schema)
    assert dropped == {"id": "id", "type": "type"}
    assert detached == ["category"]
    assert "id" not in schema["slots"] and "type" not in schema["slots"]
    assert "is_a" not in schema["slots"]["category"]
    # name and description stay: their IRIs differ from LOKF's
    assert "name" in schema["slots"] and "description" in schema["slots"]
    # the class still lists id and type, now LOKF's
    assert schema["classes"]["entity"]["slots"][:2] == ["id", "type"]


def test_drop_twins_points_a_differently_named_identifier_at_lokfs_id():
    schema = {
        "classes": {"thing": {"slots": ["identifier", "label"]}},
        "slots": {"identifier": {"identifier": True}, "label": {}},
    }
    dropped, _ = A.drop_twins(schema)
    assert dropped == {"identifier": "id"}
    assert schema["classes"]["thing"]["slots"] == ["id", "label"]


def test_drop_twins_replaces_an_identifier_attribute_with_lokfs_id():
    schema = {"classes": {"thing": {"attributes": {"uid": {"identifier": True}, "n": {}}}}, "slots": {}}
    dropped, _ = A.drop_twins(schema)
    assert dropped == {"uid": "id"}
    assert schema["classes"]["thing"] == {"attributes": {"n": {}}, "slots": ["id"]}


def test_rename_shared_refuses_a_name_the_vocabulary_already_has():
    schema = {"default_prefix": "v", "prefixes": {"v": "https://ex.org/v/"}, "slots": {"license": {}, "v_license": {}}}
    with pytest.raises(ValueError, match="v_license"):
        A.rename_shared(schema, {"slots": ["license"]}, "v")


def test_demote_designators_leaves_category_an_ordinary_slot():
    schema = _folded()
    A.drop_twins(schema)
    assert A.demote_designators(schema) == ["category"]
    assert "designates_type" not in schema["slots"]["category"]
    assert "is_class_field" not in schema["slots"]["category"]
    assert schema["slots"]["category"]["range"] == "uriorcurie"


def test_rename_shared_keeps_iris_and_follows_every_reference():
    schema = _folded()
    A.drop_twins(schema)
    renamed = A.rename_shared(schema, A.shared_names(schema, load_schema(LOKF)), "vocab")
    assert renamed == {
        "dataset": "VocabDataset", "unit": "vocab_unit", "name": "vocab_name",
        "description": "vocab_description", "license": "vocab_license",
    }
    assert schema["types"]["vocab_unit"] == {"typeof": "string", "aliases": ["unit"]}  # no uri pinned on a type
    assert schema["slots"]["symbol"]["range"] == "vocab_unit"
    slots, classes = schema["slots"], schema["classes"]
    assert slots["vocab_license"]["slot_uri"] == "vocab:license"  # pinned, was implicit
    assert slots["vocab_name"]["slot_uri"] == "rdfs:label"  # explicit, kept
    assert slots["vocab_license"]["aliases"] == ["license"]
    assert classes["VocabDataset"]["class_uri"] == "vocab:Dataset"
    assert classes["named thing"]["slots"] == ["vocab_license"]
    assert "vocab_license" in classes["named thing"]["slot_usage"]
    assert slots["described in"]["any_of"][0] == {"range": "VocabDataset"}
    assert classes["entity"]["slots"] == ["id", "type", "vocab_name", "vocab_description", "category", "has attribute"]


def test_find_roots_picks_the_rootless_class_with_an_identifier():
    schema = _folded()
    A.drop_twins(schema)
    assert A.find_roots(schema) == ["entity"]  # not the mixin, not edge


def test_find_roots_sees_an_identifier_a_mixin_supplies():
    schema = {"classes": {"identified": {"mixin": True, "slots": ["id"]}, "thing": {"mixins": ["identified"]}, "edge": {}}}
    assert A.find_roots(schema) == ["thing"]


def test_canonical_names_camelcase_classes_underscore_slots_and_follow_references():
    schema = _folded()
    collided, mapping = A.canonical_names(schema, "v")
    assert collided == {}
    assert mapping == {
        "entity": "Entity", "named thing": "NamedThing", "gene": "Gene",
        "organism taxon": "OrganismTaxon", "dataset": "Dataset", "taggable": "Taggable",
        "edge": "Edge", "in taxon": "in_taxon", "described in": "described_in",
        "has attribute": "has_attribute",
    }
    assert schema["classes"]["Gene"]["is_a"] == "NamedThing"
    assert schema["classes"]["Gene"]["slots"] == ["symbol", "in_taxon", "described_in"]
    assert schema["slots"]["in_taxon"]["range"] == "OrganismTaxon"
    assert schema["slots"]["subject"]["range"] == "Entity"


@pytest.mark.parametrize(
    "section, names, kept, old, renamed, uri_key, uri",
    [
        # The canonical spelling keeps its name; the other is renamed with the prefix, IRI pinned.
        ("classes", ["knowledge graph", "KnowledgeGraph"], "KnowledgeGraph", "knowledge graph", "VKnowledgeGraph", "class_uri", "v:KnowledgeGraph"),
        ("slots", ["in taxon", "in_taxon"], "in_taxon", "in taxon", "v_in_taxon", "slot_uri", "v:in_taxon"),
        # Neither canonical: the first keeps its name, canonicalised; the second is renamed.
        ("classes", ["sample record", "sample_record"], "SampleRecord", "sample_record", "VSampleRecord", "class_uri", "v:SampleRecord"),
    ],
)
def test_canonical_names_renames_all_but_one_of_the_names_with_one_form(section, names, kept, old, renamed, uri_key, uri):
    schema = {"default_prefix": "v", "prefixes": {"v": "https://v.example/"}, section: {n: {} for n in names}}
    collided, mapping = A.canonical_names(schema, "v")
    assert collided == {old: renamed}
    assert set(schema[section]) == {kept, renamed}
    assert schema[section][renamed] == {uri_key: uri, "aliases": [old]}
    assert old not in mapping  # renamed once, as a collision, not again as canonical


def test_adapt_is_deterministic_and_reports_every_move():
    one, report = A.adapt(VOCAB)
    two, _ = A.adapt(VOCAB)
    assert A.dump(one) == A.dump(two)
    assert report.roots == ["Entity"]
    assert report.dropped == {"id": "id", "type": "type"}
    assert report.demoted == ["category"]
    assert report.detached == ["category"]
    assert report.tree_roots == ["Edge"]
    assert "tree_root" not in one["classes"]["Edge"]
    assert one["classes"]["Entity"]["is_a"] == "Concept"
    assert one["name"] == "vocabulary-with-root_lokf"
    assert one["id"] == "https://ex.org/schema/vocab-lokf"
    assert one["notes"][-1].startswith("Adapted for LOKF by `lokf adapt`.")
    text = A.dump(one, A.header(report))
    assert text.startswith("# Generated by `lokf adapt` from vocabulary-with-root.yaml (vocabulary_with_root 1.2.3)")


def test_adapt_honours_root_and_reports_an_unknown_one():
    schema, report = A.adapt(VOCAB, roots=["edge"])
    assert report.roots == ["Edge"]
    assert schema["classes"]["Edge"]["is_a"] == "Concept"
    assert "is_a" not in schema["classes"]["Entity"]
    _, report = A.adapt(VOCAB, roots=["nonesuch"])
    assert report.problems == ["--root names no class: Nonesuch"]


def test_adapt_takes_a_renamed_root_by_its_own_name():
    schema, report = A.adapt(VOCAB, roots=["dataset"])
    assert report.problems == []
    assert report.roots == ["VocabDataset"]
    assert schema["classes"]["VocabDataset"]["is_a"] == "Concept"


# --- end to end ------------------------------------------------------------------

def _adapted(tmp_path) -> pathlib.Path:
    """The copy, beside the pinned lokf.yaml its `lokf` import names."""
    (tmp_path / "lokf.yaml").write_text(LOKF.read_text(encoding="utf-8"), encoding="utf-8")
    schema, report = A.adapt(VOCAB, name="vocab_lokf")
    out = tmp_path / "vocab_lokf.yaml"
    out.write_text(A.dump(schema, A.header(report)), encoding="utf-8")
    return out


def _domain(tmp_path) -> pathlib.Path:
    """A domain schema that imports lokf and the copy, and declares nothing."""
    domain = tmp_path / "genomics.yaml"
    domain.write_text(
        "id: https://ex.org/schema/genomics\nname: genomics\n"
        "imports: [linkml:types, lokf, vocab_lokf]\n"
        "default_prefix: genomics\n"
        "prefixes: {genomics: https://ex.org/schema/genomics/, linkml: https://w3id.org/linkml/}\n",
        encoding="utf-8",
    )
    return domain


def _bundle(tmp_path, taxon_target="taxa/human") -> pathlib.Path:
    kb = tmp_path / "knowledge"
    (kb / "genes").mkdir(parents=True, exist_ok=True)
    (kb / "taxa").mkdir(exist_ok=True)
    (kb / "index.md").write_text("---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8")
    (kb / "taxa" / "human.md").write_text(
        "---\ntype: OrganismTaxon\ntitle: Human\ncategory: [vocab:OrganismTaxon]\n---\n\n# Human\n",
        encoding="utf-8",
    )
    (kb / "genes" / "brca1.md").write_text(
        "---\ntype: Gene\ntitle: BRCA1\ncategory: [vocab:Gene]\nvocab_name: BRCA1\n"
        f"symbol: BRCA1\nin_taxon: [{taxon_target}]\nvocab_license: CC0\nweight: 1.5\n---\n\n# BRCA1\n",
        encoding="utf-8",
    )
    return kb


def test_verify_finds_nothing_wrong_with_the_copy(tmp_path):
    out = _adapted(tmp_path)
    assert A.verify(out, LOKF) == []
    assert A.shared_names(yaml.safe_load(out.read_text()), load_schema(LOKF)) == {}


def test_verify_reports_a_name_still_shared_and_a_dangling_reference(tmp_path):
    out = _adapted(tmp_path)
    schema = yaml.safe_load(out.read_text())
    schema["slots"]["license"] = {}
    schema["slots"]["symbol"]["range"] = "Nonesuch"
    out.write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")
    problems = A.verify(out, LOKF)
    assert any("slots still shared" in p and "license" in p for p in problems)
    assert any("Nonesuch" in p for p in problems)


def test_the_copy_is_a_domain_schema_and_a_schema_that_imports_it_is_another(tmp_path):
    copy, kb = _adapted(tmp_path), _bundle(tmp_path)
    for schema in (copy, _domain(tmp_path)):
        result = runner.invoke(app, ["validate", str(kb), "--schema", str(schema), "--check-refs"])
        assert result.exit_code == 0, result.output
        assert result.output.startswith("OK")


def test_check_refs_covers_the_vocabularys_relation_slots(tmp_path):
    _adapted(tmp_path)
    domain, kb = _domain(tmp_path), _bundle(tmp_path, taxon_target="taxa/nope")
    result = runner.invoke(app, ["validate", str(kb), "--schema", str(domain), "--check-refs"])
    assert result.exit_code != 0
    assert "`in_taxon` target does not resolve" in result.output


def test_check_refs_reads_a_curie_as_the_iri_it_expands_to(tmp_path):
    """`NCBITaxon:9606` names an external taxon, as the projection reads it;
    a CURIE under the bundle's own prefix is still the bundle's to resolve."""
    _adapted(tmp_path)
    domain = _domain(tmp_path)
    domain.write_text(
        domain.read_text().replace(
            "prefixes: {", "prefixes: {NCBITaxon: http://purl.obolibrary.org/obo/NCBITaxon_, kb: https://ex.org/kb/, "
        ),
        encoding="utf-8",
    )
    kb = _bundle(tmp_path, taxon_target="NCBITaxon:9606")
    result = runner.invoke(app, ["validate", str(kb), "--schema", str(domain), "--check-refs"])
    assert result.exit_code == 0, result.output
    kb = _bundle(tmp_path, taxon_target="kb:taxa/nope")
    result = runner.invoke(app, ["validate", str(kb), "--schema", str(domain), "--check-refs"])
    assert result.exit_code != 0
    assert "kb:taxa/nope" in result.output


def test_the_copy_projects_under_the_vocabularys_iris(tmp_path):
    _adapted(tmp_path)
    domain, kb = _domain(tmp_path), _bundle(tmp_path)
    result = runner.invoke(app, ["convert", str(kb / "genes" / "brca1.md"), "-f", "nt", "--schema", str(domain)])
    assert result.exit_code == 0, result.output
    nt = result.stdout
    assert "<https://ex.org/schema/vocab/Gene>" in nt  # the class, not lokf:Concept
    assert "additionalType" not in nt
    assert '<http://www.w3.org/2000/01/rdf-schema#label> "BRCA1"' in nt  # vocab_name kept rdfs:label
    assert "<https://ex.org/schema/vocab/in_taxon> <https://ex.org/kb/taxa/human>" in nt  # an IRI
    assert "<https://ex.org/schema/vocab/license>" in nt  # renamed slot, original IRI
    assert "w3id.org/lokf/vocab_license" not in nt


# --- the command ----------------------------------------------------------------

def test_cli_writes_beside_the_input_by_default(tmp_path):
    vocab = tmp_path / "vocab.yaml"
    vocab.write_text(VOCAB.read_text(encoding="utf-8"), encoding="utf-8")
    sibling = FIXTURES / "vocabulary-with-root-attributes.yaml"
    (tmp_path / sibling.name).write_text(sibling.read_text(encoding="utf-8"), encoding="utf-8")
    result = runner.invoke(app, ["adapt", str(vocab)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "vocab_lokf.yaml").exists()
    assert "re-rooted on Concept:    Entity" in result.output
    assert "imports: [linkml:types, lokf, vocab_lokf]" in result.output


def test_cli_dry_run_writes_nothing_but_still_verifies(tmp_path):
    out = tmp_path / "copy.yaml"
    result = runner.invoke(app, ["adapt", str(VOCAB), "-o", str(out), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "renamed, IRIs kept:" in result.output
    assert "verified beside lokf.yaml (dry run, nothing written)" in result.output
    assert not out.exists()


def test_cli_creates_the_output_directory(tmp_path):
    out = tmp_path / "new" / "copy.yaml"
    result = runner.invoke(app, ["adapt", str(VOCAB), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_cli_refuses_to_overwrite_the_input(tmp_path):
    vocab = tmp_path / "v.yaml"
    vocab.write_text(VOCAB.read_text(encoding="utf-8"), encoding="utf-8")
    result = runner.invoke(app, ["adapt", str(vocab), "-o", str(vocab)])
    assert result.exit_code == 2
    assert "is the input" in result.output


def test_cli_reports_a_malformed_vocabulary(tmp_path):
    vocab = tmp_path / "v.yaml"
    vocab.write_text("- just\n- a list\n", encoding="utf-8")
    result = runner.invoke(app, ["adapt", str(vocab), "-o", str(tmp_path / "x.yaml")])
    assert result.exit_code == 1
    assert "not a LinkML schema" in result.output


def test_cli_check_passes_a_fresh_copy_and_fails_a_stale_or_missing_one(tmp_path):
    out = tmp_path / "copy.yaml"
    assert runner.invoke(app, ["adapt", str(VOCAB), "-o", str(out), "--check"]).exit_code == 1
    assert runner.invoke(app, ["adapt", str(VOCAB), "-o", str(out)]).exit_code == 0
    assert runner.invoke(app, ["adapt", str(VOCAB), "-o", str(out), "--check"]).exit_code == 0
    out.write_text(out.read_text() + "\n# edited\n", encoding="utf-8")
    result = runner.invoke(app, ["adapt", str(VOCAB), "-o", str(out), "--check"])
    assert result.exit_code == 1
    assert "is stale" in result.output


def test_cli_exits_one_when_root_names_no_class(tmp_path):
    result = runner.invoke(app, ["adapt", str(VOCAB), "-o", str(tmp_path / "x.yaml"), "--root", "nonesuch"])
    assert result.exit_code == 1
    assert "--root names no class" in result.output


_BROKEN = (
    "id: https://ex.org/v\nname: v\ndefault_prefix: v\nimports: [linkml:types]\n"
    "prefixes: {v: https://ex.org/v/, linkml: https://w3id.org/linkml/}\n"
    "classes:\n  thing: {slots: [uid, part]}\n"
    "slots:\n  uid: {identifier: true}\n  part: {range: nonesuch}\n"
)


def test_cli_leaves_an_existing_copy_when_the_new_one_fails_to_verify(tmp_path):
    vocab = tmp_path / "v.yaml"
    vocab.write_text(_BROKEN, encoding="utf-8")
    out = tmp_path / "out" / "v_lokf.yaml"
    out.parent.mkdir()
    out.write_text("# the copy that worked\n", encoding="utf-8")
    result = runner.invoke(app, ["adapt", str(vocab), "-o", str(out)])
    assert result.exit_code == 1
    assert "nonesuch is not defined" in result.output
    assert out.read_text(encoding="utf-8") == "# the copy that worked\n"
    assert [p.name for p in out.parent.iterdir()] == ["v_lokf.yaml"]  # no candidate left behind


def test_cli_renames_a_canonical_name_collision_and_reports_it(tmp_path):
    vocab = tmp_path / "v.yaml"
    vocab.write_text(_BROKEN.replace("part: {range: nonesuch}", "part: {}\n  has part: {}\n  has_part: {}"), encoding="utf-8")
    out = tmp_path / "v_lokf.yaml"
    result = runner.invoke(app, ["adapt", str(vocab), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert "one canonical form:      has part -> v_has_part" in result.output
    copy = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert {"has_part", "v_has_part"} <= set(copy["slots"])
    assert copy["slots"]["v_has_part"]["aliases"] == ["has part"]


# --- biolink-model, when fetched -------------------------------------------------

BIOLINK = ROOT / "examples" / "biolink"


def test_biolink_round_trip(tmp_path):
    upstream = BIOLINK / "upstream" / "biolink_model.yaml"
    if not upstream.exists():
        pytest.skip("run `just biolink` to fetch biolink-model first")
    schema, report = A.adapt(upstream, name="biolink_lokf")
    assert report.roots == ["Entity"]
    assert report.dropped == {"id": "id", "type": "type"}
    assert report.demoted == ["category"]
    assert {"name", "description", "license", "agent", "dataset"} <= set(report.renamed)
    assert report.collided == {"knowledge graph": "BiolinkKnowledgeGraph"}  # biolink 4.4.4 has both spellings
    copy = BIOLINK / "biolink_lokf.yaml"
    copy.write_text(A.dump(schema, A.header(report)), encoding="utf-8")
    assert A.verify(copy, LOKF) == []
    # The copy is the LOKF domain schema: nothing of the bundle's own imports it.
    result = runner.invoke(app, ["validate", str(BIOLINK / "knowledge"), "--schema", str(copy), "--check-refs"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["convert", str(BIOLINK / "knowledge"), "-f", "nt", "--schema", str(copy)])
    assert result.exit_code == 0, result.output
    assert "<https://w3id.org/biolink/vocab/Gene>" in result.stdout
