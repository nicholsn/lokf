"""Tests for the ``lokf`` CLI (Typer) via ``typer.testing.CliRunner``.

Only side-effect-free commands are driven here — convert, query, and vocab.
serve and mcp block, so they are deliberately not invoked.
"""
from __future__ import annotations

import json
import pathlib

from typer.testing import CliRunner

from lokf.cli import app

BUNDLE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge"
METRIC = BUNDLE / "metrics" / "weekly-active-users.md"

_SELECT = "SELECT ?name WHERE { ?m a lokf:Metric ; schema:name ?name }"
_CONSTRUCT = (
    "CONSTRUCT { ?s prov:wasDerivedFrom ?o } WHERE { ?s prov:wasDerivedFrom ?o }"
)

runner = CliRunner()


# -- version ----------------------------------------------------------------
def test_version_prints_package_version():
    """--version (and -V) print the installed lokf version and exit 0."""
    from importlib.metadata import version

    expected = f"lokf {version('lokf')}"
    for flag in ("--version", "-V"):
        result = runner.invoke(app, [flag])
        assert result.exit_code == 0
        assert result.stdout.strip() == expected


# -- convert ----------------------------------------------------------------
def test_convert_ttl_contains_metric_curie():
    """convert <metric> -f ttl emits Turtle carrying lokf:Metric."""
    result = runner.invoke(app, ["convert", str(METRIC), "-f", "ttl"])
    assert result.exit_code == 0
    assert "lokf:Metric" in result.stdout


def test_convert_nt_non_empty():
    """convert -f nt emits non-empty N-Triples."""
    result = runner.invoke(app, ["convert", str(METRIC), "-f", "nt"])
    assert result.exit_code == 0
    assert result.stdout.strip()
    # N-Triples lines end in a period.
    assert result.stdout.strip().endswith(".")


def test_convert_jsonld_is_json():
    """convert -f jsonld emits parseable JSON-LD."""
    result = runner.invoke(app, ["convert", str(METRIC), "-f", "jsonld"])
    assert result.exit_code == 0
    doc = json.loads(result.stdout)
    assert doc  # non-empty JSON structure


def test_convert_bad_format_exit_2():
    """An unknown --format exits 2 (ValueError -> typer.Exit(2))."""
    result = runner.invoke(app, ["convert", str(METRIC), "--format", "bogus"])
    assert result.exit_code == 2


def test_convert_output_writes_file(tmp_path):
    """convert -o <file> writes the RDF to that path and confirms on stdout."""
    out = tmp_path / "out.ttl"
    result = runner.invoke(app, ["convert", str(METRIC), "-o", str(out)])
    assert result.exit_code == 0
    assert f"wrote {out}" in result.stdout
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "lokf:Metric" in text


# -- validate ---------------------------------------------------------------
def test_validate_reference_bundle_ok():
    """validate <bundle> assembles and validates against KnowledgeBundle."""
    result = runner.invoke(app, ["validate", str(BUNDLE)])
    assert result.exit_code == 0
    assert "validate against KnowledgeBundle" in result.stdout


def test_validate_without_linkml_hints_at_the_build_extra(monkeypatch):
    """A lean install has no LinkML: exit 1 with an install hint, not a traceback."""
    import sys

    # `None` in sys.modules makes the `from linkml.validator import ...` raise
    # ModuleNotFoundError, which is what a lean install raises.
    monkeypatch.setitem(sys.modules, "linkml.validator", None)
    result = runner.invoke(app, ["validate", str(BUNDLE)])
    assert result.exit_code == 1
    # `result.output`, not `.stdout`: the hint goes to stderr.
    assert "lokf[build]" in result.output


def test_validate_reports_a_schema_violation(tmp_path):
    """An unknown frontmatter key fails closed, with the offending key named."""
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "term.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: T\nseeAlso: invented\n---\n\n# T\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "[ERROR]" in result.output
    assert "seeAlso" in result.output


def test_validate_names_the_offending_key_even_with_a_real_type(tmp_path):
    """A stock class (no custom type) with one undeclared key: jsonschema's
    own `best_match` ties across LOKF's ~15 anyOf branches and gives up
    (regression for lokf-issue.md) - `lokf validate` must still name it."""
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "term.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: T\ndescription: d\nects: 5\n---\n\n# T\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "[ERROR]" in result.output
    assert "ects" in result.output
    assert "GlossaryTerm" in result.output


def test_validate_points_at_schema_for_an_unknown_type(tmp_path):
    """A `type:` naming no declared class should point at --schema, not just
    dump the generic anyOf failure."""
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "term.md").write_text(
        "---\ntype: CustomThing\ntitle: T\ndescription: d\n---\n\n# T\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "imports: [lokf]" in result.output
    assert "--schema" in result.output


def test_validate_accepts_source_with_supporting_text(tmp_path):
    """A `sources[].supporting_text` excerpt validates against the schema.

    Regression coverage for the Source class's `supporting_text` slot
    (linkml:excerpt) and `resource`'s dcterms:source annotation added
    alongside it - both are additive, optional fields and must not make an
    otherwise-valid concept fail.
    """
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "term.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: T\n"
        "sources:\n  - resource: https://ex.org/rfc\n"
        "    supporting_text: the exact quoted sentence\n"
        "---\n\n# T\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 0
    assert "validate against KnowledgeBundle" in result.stdout


def test_validate_reports_a_warning_without_failing(monkeypatch):
    """`linkml-validate` exits 0 unless a result is ERROR; so does this."""
    from linkml.validator.report import Severity, ValidationResult

    warning = ValidationResult(
        type="test", severity=Severity.WARN, message="just a warning"
    )
    monkeypatch.setattr(
        "linkml.validator.validate",
        lambda *a, **kw: type("R", (), {"results": [warning]})(),
    )
    result = runner.invoke(app, ["validate", str(BUNDLE)])
    assert result.exit_code == 0
    assert "[WARN] just a warning" in result.output
    assert "validate against KnowledgeBundle" in result.stdout


def test_validate_missing_bundle_nonzero_exit():
    """A non-existent bundle directory is rejected before validation."""
    result = runner.invoke(app, ["validate", "does-not-exist"])
    assert result.exit_code != 0


def test_validate_rejects_malformed_actor_string(tmp_path):
    """`generated.by` must follow the OKF actor-string convention.

    Regression coverage for the `by` slot's new `pattern` constraint: trust
    tiers (lokf.trust) derive from the `human:`/`process:` prefix by string
    inspection, so an actor string that doesn't follow the convention used
    to pass schema validation and silently be misclassified.
    """
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "term.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        'generated: { by: "John Smith", at: 2026-06-01T00:00:00Z }\n---\n\n# T\n',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "[ERROR]" in result.output

def test_validate_rejects_malformed_email(tmp_path):
    """`email` must look like an email address; regression for its new pattern."""
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "term.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        "author:\n  - type: Person\n    id: https://ex.org/people/x\n"
        "    name: X\n    email: not-an-email\n---\n\n# T\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "[ERROR]" in result.output

def test_validate_check_ids_rejects_two_files_declaring_one_id(tmp_path):
    """Two files with one `id` each validate alone and then merge into one
    subject in the graph, which neither JSON Schema nor SHACL can see; the
    bundle can, and `--check-ids` must say which files. Without the flag the
    schema is the whole verdict, as OKF's permissive stance intends."""
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    a = "---\nid: https://ex.org/kb/a\ntype: GlossaryTerm\ntitle: A\n---\n\n# A\n"
    (tmp_path / "a.md").write_text(a, encoding="utf-8")
    (tmp_path / "a (conflicted copy).md").write_text(a, encoding="utf-8")
    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 0
    result = runner.invoke(app, ["validate", str(tmp_path), "--check-ids"])
    assert result.exit_code == 1
    assert (
        "[ERROR] id declared by more than one file: https://ex.org/kb/a "
        "(a (conflicted copy), a)"
    ) in result.output


def test_validate_check_ids_passes_the_reference_bundle():
    result = runner.invoke(app, ["validate", str(BUNDLE), "--check-ids"])
    assert result.exit_code == 0
    assert "Every IRI is declared by one file." in result.stdout


def test_validate_rejects_unknown_http_method(tmp_path):
    """`http_method` must be a real IANA verb; regression for the HttpMethod enum."""
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "svc.md").write_text(
        "---\ntype: Service\ntitle: S\nhttp_method: FETCH\n---\n\n# S\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "[ERROR]" in result.output


# -- --check-refs (referential integrity, issue #64) -------------------------
def _kb(tmp_path, term: str, extra_files: dict | None = None):
    """A minimal bundle: index.md, one resolvable concept, plus *term*."""
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "real.md").write_text(
        "---\ntype: GlossaryTerm\ntitle: Real\ndefinition: d\n---\n\n# Real\n",
        encoding="utf-8",
    )
    (tmp_path / "term.md").write_text(term, encoding="utf-8")
    for name, text in (extra_files or {}).items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def test_check_refs_passes_on_the_reference_bundle():
    """The shipped bundle cites an off-site `definedBy`; that must stay valid."""
    result = runner.invoke(app, ["validate", str(BUNDLE), "--check-refs"])
    assert result.exit_code == 0
    assert "All in-namespace relation targets resolve." in result.stdout


def test_check_refs_catches_a_fabricated_in_namespace_target(tmp_path):
    """The issue's actual failure: a stale/invented IRI under the bundle's own
    base_iri passes JSON Schema as a valid string."""
    kb = _kb(
        tmp_path,
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        "isPartOf: [https://ex.org/kb/does-not-exist]\n---\n\n# T\n",
    )
    assert runner.invoke(app, ["validate", str(kb)]).exit_code == 0  # schema alone can't see it
    checked = runner.invoke(app, ["validate", str(kb), "--check-refs"])
    assert checked.exit_code == 1
    assert "isPartOf" in checked.output and "does-not-exist" in checked.output


def test_check_refs_catches_a_dangling_relative_ref(tmp_path):
    kb = _kb(
        tmp_path,
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        "dependsOn: [missing-concept]\n---\n\n# T\n",
    )
    result = runner.invoke(app, ["validate", str(kb), "--check-refs"])
    assert result.exit_code == 1
    assert "missing-concept" in result.output


def test_check_refs_accepts_a_resolvable_relative_ref(tmp_path):
    kb = _kb(
        tmp_path,
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        "dependsOn: [real]\n---\n\n# T\n",
    )
    assert runner.invoke(app, ["validate", str(kb), "--check-refs"]).exit_code == 0


def test_check_refs_ignores_external_resources(tmp_path):
    """`definedBy`/`source` are defined as taking an external resource, so an
    off-site URL is correct usage - flagging it would make the check unusable
    on any bundle that cites the outside world."""
    kb = _kb(
        tmp_path,
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        "definedBy: [https://external.example/rfc/spec]\n"
        "source: [https://other.example/paper]\n---\n\n# T\n",
    )
    assert runner.invoke(app, ["validate", str(kb), "--check-refs"]).exit_code == 0


def test_check_refs_catches_a_dangling_generic_relation_target(tmp_path):
    """`relations[].target` is not a named slot, so it needs its own pass."""
    kb = _kb(
        tmp_path,
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        "relations:\n  - predicate: relatedTo\n"
        "    target: https://ex.org/kb/also-missing\n---\n\n# T\n",
    )
    result = runner.invoke(app, ["validate", str(kb), "--check-refs"])
    assert result.exit_code == 1
    assert "relations" in result.output and "also-missing" in result.output


def test_check_refs_allows_free_text_in_measures(tmp_path):
    """`measures` is documented as accepting "a concept IRI or description"."""
    (tmp_path / "index.md").write_text(
        "---\nbase_iri: https://ex.org/kb/\ntitle: KB\n---\n", encoding="utf-8"
    )
    (tmp_path / "m.md").write_text(
        "---\ntype: Metric\ntitle: M\nunit: users\n"
        "measures:\n  - the number of distinct home page visitors\n---\n\n# M\n",
        encoding="utf-8",
    )
    assert runner.invoke(app, ["validate", str(tmp_path), "--check-refs"]).exit_code == 0


def test_check_refs_is_off_by_default(tmp_path):
    """Opt-in: a dangling target must not start failing existing bundles."""
    kb = _kb(
        tmp_path,
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        "isPartOf: [https://ex.org/kb/nope]\n---\n\n# T\n",
    )
    result = runner.invoke(app, ["validate", str(kb)])
    assert result.exit_code == 0
    assert "nope" not in result.output


def test_check_refs_honours_an_explicit_schema(tmp_path):
    """The vocabulary must come from the schema actually validated against, or
    a --schema that renames a relation slot would silently check the wrong one."""
    lokf_yaml = pathlib.Path(__file__).resolve().parents[1] / "lokf.yaml"
    text = lokf_yaml.read_text(encoding="utf-8")
    # Rename only the isPartOf slot definition and its declaration on Concept -
    # anchored on exact indentation so the schema:isPartOf/dcterms:isPartOf
    # CURIEs and the RelationType permissible value are left alone.
    assert text.count("\n  isPartOf:\n") == 1
    assert text.count("\n      - isPartOf\n") == 1
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        text.replace("\n  isPartOf:\n", "\n  customPartOf:\n").replace(
            "\n      - isPartOf\n", "\n      - customPartOf\n"
        ),
        encoding="utf-8",
    )
    kb = _kb(
        tmp_path,
        "---\ntype: GlossaryTerm\ntitle: T\ndefinition: d\n"
        "customPartOf: [https://ex.org/kb/does-not-exist]\n---\n\n# T\n",
    )
    result = runner.invoke(
        app, ["validate", str(kb), "--schema", str(custom), "--check-refs"]
    )
    assert result.exit_code == 1
    assert "customPartOf" in result.output and "does-not-exist" in result.output


# -- query ------------------------------------------------------------------
def test_query_select_table_contains_wau():
    """query <bundle> <SELECT> prints a table with the metric name."""
    result = runner.invoke(app, ["query", str(BUNDLE), _SELECT])
    assert result.exit_code == 0
    assert "Weekly Active Users" in result.stdout
    assert "name" in result.stdout  # column header


def test_query_json_valid():
    """query -f json emits valid SPARQL-results JSON."""
    result = runner.invoke(app, ["query", str(BUNDLE), _SELECT, "-f", "json"])
    assert result.exit_code == 0
    doc = json.loads(result.stdout)
    assert doc["head"]["vars"] == ["name"]
    assert doc["results"]["bindings"][0]["name"]["value"] == "Weekly Active Users"


def test_query_construct_turtle():
    """A CONSTRUCT query prints Turtle."""
    result = runner.invoke(app, ["query", str(BUNDLE), _CONSTRUCT])
    assert result.exit_code == 0
    assert "wasDerivedFrom" in result.stdout or "prov:" in result.stdout


def test_query_ask_in_the_default_table_format():
    """An ASK answer is a boolean; the default format used to crash on it."""
    result = runner.invoke(app, ["query", str(BUNDLE), "ASK { ?s ?p ?o }"])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "true"


def test_query_ask_false_still_exits_zero():
    """A false answer is an answer, not a failure."""
    result = runner.invoke(
        app, ["query", str(BUNDLE), "ASK { ?s a lokf:NoSuchClass }"]
    )
    assert result.exit_code == 0
    assert result.stdout.strip() == "false"


def test_query_malformed_sparql_nonzero_exit():
    """A malformed SPARQL query exits non-zero."""
    result = runner.invoke(app, ["query", str(BUNDLE), "SELEC broken"])
    assert result.exit_code != 0


# -- vocab ------------------------------------------------------------------
def test_vocab_lists_relations():
    """vocab prints the relation vocabulary (known relation names present)."""
    result = runner.invoke(app, ["vocab"])
    assert result.exit_code == 0
    assert "derivedFrom" in result.stdout
    assert "dependsOn" in result.stdout


def test_vocab_json_valid():
    """vocab --json emits a parseable list of relation records."""
    result = runner.invoke(app, ["vocab", "--json"])
    assert result.exit_code == 0
    records = json.loads(result.stdout)
    assert isinstance(records, list) and records
    assert {"name", "curie", "uri"} <= set(records[0])


# -- export -----------------------------------------------------------------
def test_export_writes_graph_and_datasets(tmp_path):
    """export writes graph.json (cytoscape) + datasets.jsonld (Dataset docs)."""
    result = runner.invoke(
        app,
        ["export", str(BUNDLE), "--out-dir", str(tmp_path), "--source-base", "https://x/"],
    )
    assert result.exit_code == 0
    graph = json.loads((tmp_path / "graph.json").read_text())
    assert len(graph["nodes"]) == 8 and len(graph["edges"]) == 12
    assert graph["meta"]["source_base"] == "https://x/"
    datasets = json.loads((tmp_path / "datasets.jsonld").read_text())
    assert len(datasets) == 2 and all(d["@type"] == "Dataset" for d in datasets)


def test_export_writes_registry_producer_contract(tmp_path):
    """export also writes graph.nt + concepts.jsonld (the registry harvest source)."""
    result = runner.invoke(app, ["export", str(BUNDLE), "--out-dir", str(tmp_path)])
    assert result.exit_code == 0

    # graph.nt is the whole bundle as N-Triples (one statement per line).
    nt = (tmp_path / "graph.nt").read_text()
    assert nt.strip() and all(
        line.endswith(" .") for line in nt.strip().splitlines()
    )

    # concepts.jsonld is one @context/@graph document carrying frontmatter + body,
    # each concept keyed by its IRI, and it round-trips to the same triples as nt.
    doc = json.loads((tmp_path / "concepts.jsonld").read_text())
    assert set(doc) == {"@context", "@graph"}
    assert len(doc["@graph"]) == 8
    assert all(c.get("id", "").startswith("http") and "body" in c for c in doc["@graph"])

    from rdflib import Graph

    g_nt = Graph().parse(str(tmp_path / "graph.nt"), format="nt")
    g_jsonld = Graph().parse(str(tmp_path / "concepts.jsonld"), format="json-ld")
    assert len(g_nt) and g_nt.isomorphic(g_jsonld)
