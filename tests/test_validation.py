"""Cross-interface regressions for the bundle validation report."""
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typer.testing import CliRunner

from lokf.cli import app
from lokf.validation import validate_bundle

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def without_directory_access(path):
    original = path.stat().st_mode
    try:
        path.chmod(0)
        if os.access(path, os.R_OK | os.X_OK):
            pytest.skip("this process can still access a mode-000 directory")
        yield
    finally:
        path.chmod(original)


@pytest.fixture
def project(tmp_path):
    # Relative imports exercise CLI and MCP discovery from different working directories.
    shutil.copyfile(ROOT / "lokf.yaml", tmp_path / "lokf.yaml")
    (tmp_path / "pyproject.toml").write_text('[tool.lokf]\nschema = "domain.yaml"\n')
    (tmp_path / "domain.yaml").write_text("""id: https://example.org/schema/profile
name: profile
imports: [course-types]
default_prefix: ex
prefixes: {ex: https://example.org/schema/}
""")
    (tmp_path / "course-types.yaml").write_text("""id: https://example.org/schema/course
name: course
imports: [lokf]
default_prefix: ex
prefixes: {ex: https://example.org/schema/}
classes:
  Course: {is_a: Concept, slots: [teacher]}
slots:
  teacher: {range: Person, slot_uri: ex:teacher}
""")
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "index.md").write_text("---\ntitle: Courses\nbase_iri: https://example.org/kb/\n---\n")
    (kb / "course.md").write_text("---\ntype: Course\ntitle: Course\nteacher: pat\n"
                                  "sources: [{resource: evidence.txt, excerpt: taught here}]\n---\n")
    (kb / "pat.md").write_text("---\ntype: Person\ntitle: Pat\n---\n")
    (tmp_path / "evidence.txt").write_text("Pat taught here.")
    return kb


def test_stdio_cli_and_live_source_coverage(project):
    kb = project
    args = {"bundle": str(kb), "root": str(kb.parent), "check_excerpts": True,
            "check_resources": True, "check_refs": True, "shacl": True}
    cli = ["validate", str(kb), "--root", str(kb.parent), "--check-excerpts", "--check-resources",
           "--check-refs", "--shacl"]

    async def run():
        params = StdioServerParameters(command=sys.executable, args=["-m", "lokf.mcp_server"], cwd=ROOT)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=60) as client:
                await client.initialize()
                tool = next(t for t in (await client.list_tools()).tools if t.name == "validate_bundle")
                assert tool.annotations.read_only_hint
                assert {"checks", "outcome", "diagnostics", "source", "schema"} <= set(tool.output_schema["properties"])

                async def call(name, arguments):
                    result = await client.call_tool(name, arguments)
                    assert not result.is_error
                    if name == "get_vocabulary" and result.structured_content is None:
                        return json.loads(result.content[0].text)
                    assert result.structured_content is not None
                    return result.structured_content

                schema = (await call("get_vocabulary", {"bundle": str(kb), "include_metadata": True}))["schema_metadata"]
                good = await call("validate_bundle", args)
                assert good["outcome"] == "valid" and good["checks"]["shacl"] == "passed"
                assert good["schema"]["revision"] == schema["revision"]
                assert good["source"]["revision"] is None and good["excerpts"]["local"] == 1
                assert CliRunner().invoke(app, cli).exit_code == 0

                (kb / "pat.md").write_text("---\ntype: GlossaryTerm\ntitle: Pat\n---\n")
                wrong = await call("validate_bundle", args)
                assert wrong["outcome"] == "invalid" and wrong["checks"]["refs"] == "passed"
                issue, = wrong["diagnostics"]
                assert (issue["code"], issue["document"], issue["field"]) == (
                    "shacl.Class", "course.md", "https://example.org/schema/teacher")
                assert CliRunner().invoke(app, cli).exit_code == 1

                (kb.parent / "evidence.txt").write_text("Changed.")
                bad = await call("validate_bundle", args)
                assert bad["schema"] == good["schema"] and bad["checks"]["shacl"] == "skipped"
                issue, = bad["diagnostics"]
                assert (issue["code"], issue["document"], issue["field"]) == (
                    "excerpt.mismatch", "course.md", "/sources/0/excerpt")
                assert CliRunner().invoke(app, cli).exit_code == 1

    asyncio.run(run())


def test_diagnostic_locations_counts_and_bounds(project):
    kb = project
    private_body = "PRIVATE BODY " * 1700
    (kb / "other.md").write_text("---\ntype: Course\nid: pat\nteacher: [123]\n---\n" + private_body)
    (kb / "pat.md").write_text("---\ntype: Person\nid: pat\nextra: true\ncreated: bad-date\n---\n")
    (kb / "course.md").write_text("---\ntype: Course\nteacher: missing\n---\n")
    opts = dict(check_ids=True, check_refs=True)
    full = validate_bundle(kb, **opts).as_dict()
    assert full["outcome"] == "invalid"
    assert "PRIVATE BODY" not in json.dumps(full)
    located = {(d["code"], d["document"], d["field"]) for d in full["diagnostics"]}
    assert ("schema.unknown_field", "pat.md", "/extra") in located
    assert ("schema.format", "pat.md", "/created") in located
    assert any(code == "schema.type" and doc == "other.md" for code, doc, _ in located)
    assert ("id.duplicate", "other.md", "/id") in located
    assert ("reference.missing", "course.md", "/teacher") in located
    assert validate_bundle(kb, **opts).as_dict() == full

    (kb / "other.md").unlink()
    (kb / "pat.md").write_text("---\ntype: Person\ntitle: Pat\n---\n")
    (kb / "log.md").write_text("## 2026-01-01\n## 2026-01-01\n")
    limited = validate_bundle(kb, max_diagnostics=1, **opts).as_dict()
    assert limited["diagnostics"][0]["severity"] == "warning"
    assert limited["diagnostics"][0]["line"] == 2
    assert limited["outcome"] == "invalid" and limited["checks"]["refs"] == "failed"
    assert limited["omitted"] == 1 and limited["diagnostic_count"] == 2


def test_invalid_identifiers_and_relations_leave_other_checks_available(project):
    (project / "index.md").write_text("---\ntitle: Courses\nbase_iri: [wrong]\n---\n")
    (project / "pat.md").write_text("---\ntype: Person\nid: [wrong]\nrelations: 3\n---\n")
    (project / "other.md").write_text("---\ntype: [Person]\n---\n")
    report = validate_bundle(project, check_ids=True, check_refs=True, check_excerpts=True)
    assert report.outcome == "invalid" and "unavailable" not in report.checks.values()
    assert report.checks["excerpts"] == "passed"
    located = {(d["document"], d["field"]) for d in report.diagnostics}
    assert {("index.md", "/base_iri"), ("pat.md", "/id"), ("pat.md", "/relations"),
            ("other.md", "/type"), ("course.md", "/teacher")} <= located


def test_unavailable_checks_and_frontmatter(project, monkeypatch):
    absent = validate_bundle(project / "absent").as_dict()
    assert absent["outcome"] == "incomplete" and absent["checks"]["schema"] == "skipped"
    assert absent["concept_count"] is None
    (project / "pat.md").write_text("---\ntype: [\n---\n")
    bad = validate_bundle(project).as_dict()
    issue, = bad["diagnostics"]
    assert (bad["outcome"], issue["code"], issue["document"]) == ("invalid", "document.frontmatter", "pat.md")
    assert issue["line"] and "Traceback" not in issue["message"]
    (project / "pat.md").write_text("---\ntype: Person\ncreated: 2025-02-31\n---\n")
    bad = validate_bundle(project)
    assert bad.outcome == "invalid" and bad.diagnostics[0]["document"] == "pat.md"
    monkeypatch.setitem(sys.modules, "pyshacl", None)
    partial = validate_bundle(project, shacl=True).as_dict()
    assert partial["outcome"] == "incomplete" and partial["checks"]["shacl"] == "unavailable"
    assert partial["diagnostics"][0]["code"] == "dependency.shacl"


def test_import_edit_during_validation_uses_one_schema(project, monkeypatch):
    from lokf import validation
    from lokf.schema import discover_vocabulary

    path = project.parent / "course-types.yaml"
    old = discover_vocabulary(project, include_metadata=True)[1]["revision"]
    validate = validation._schema_findings

    def edit_after_capture(*args):
        path.write_text(path.read_text().replace("range: Person", "range: GlossaryTerm"))
        validate(*args)

    with monkeypatch.context() as patch:
        patch.setattr(validation, "_schema_findings", edit_after_capture)
        original = validate_bundle(project, check_refs=True, shacl=True).as_dict()
    changed = validate_bundle(project, check_refs=True, shacl=True).as_dict()
    assert original["schema"]["revision"] == old and original["outcome"] == "valid"
    assert changed["schema"]["revision"] != old and changed["checks"]["shacl"] == "failed"


def test_unreadable_evidence_preserves_verdict_and_counts(project, monkeypatch):
    evidence = project.parent / "evidence.txt"
    original_open = Path.open

    def deny_read(path, *args, **kwargs):
        if path == evidence:
            raise PermissionError("read permission denied")
        return original_open(path, *args, **kwargs)

    options = dict(check_excerpts=True, root=project.parent)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", deny_read)
        report = validate_bundle(project, **options)
        assert (report.outcome, report.checks["excerpts"], report.excerpts["local"]) == ("incomplete", "unavailable", 0)
        issue, = report.diagnostics
        assert (issue["code"], issue["document"], issue["field"]) == ("excerpt.unavailable", "course.md", "/sources/0/excerpt")
        (project / "log.md").write_text("## invalid date\n")
        assert validate_bundle(project, **options).outcome == "invalid"

    (project / "log.md").unlink()
    evidence.write_bytes(b"binary\x00data")
    report = validate_bundle(project, **options)
    assert (report.outcome, report.checks["excerpts"], report.excerpts["local"]) == ("invalid", "failed", 0)


def test_partial_bundle_scan_cannot_certify_content(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "index.md").write_text("---\ntitle: KB\nbase_iri: https://example.org/kb/\n---\n")
    (nested / "untyped.md").write_text("---\ntitle: Pat\n---\n")
    original = validate_bundle(tmp_path).as_dict()
    assert original["outcome"] == "invalid" and original["concept_count"] == 1
    assert original["diagnostics"][0]["field"] == "/type"
    with without_directory_access(nested):
        partial = validate_bundle(tmp_path)
        assert (partial.outcome, partial.checks["input"], partial.concept_count) == ("incomplete", "unavailable", None)
        assert partial.checks["schema"] == "skipped"
        assert "nested" in partial.diagnostics[0]["message"]
    assert validate_bundle(tmp_path).as_dict() == original


def test_inaccessible_resource_directory_and_partial_globs(project):
    evidence = project.parent / "evidence"
    hidden, visible = evidence / "hidden", evidence / "visible"
    for folder in (hidden, visible):
        folder.mkdir(parents=True)
        (folder / "quote.txt").write_text("taught here")
    course = project / "course.md"
    course.write_text(course.read_text().replace(
        "sources: [{resource: evidence.txt, excerpt: taught here}]",
        "sources:\n  - {resource: evidence/hidden/quote.txt, excerpt: taught here}\n"
        "  - {resource: 'evidence/hidden/*.txt'}\n  - {resource: 'evidence/*/*.txt'}\n"
        "  - {resource: 'evidence/**/quote.txt'}\n  - {resource: 'evidence/visible/*.txt'}"))
    options = dict(root=project.parent, check_resources=True, check_excerpts=True)
    original = validate_bundle(project, **options).as_dict()
    assert original["outcome"] == "valid" and original["resources"]["local"] == 5
    with without_directory_access(hidden):
        partial = validate_bundle(project, **options)
        assert partial.outcome == "incomplete" and partial.checks["resources"] == partial.checks["excerpts"] == "unavailable"
        assert {(d["document"], d["field"]) for d in partial.diagnostics if d["code"] == "resource.unavailable"} == {
            ("course.md", f"/sources/{i}/resource") for i in range(4)}
        assert partial.resources == {"local": 1, "remote": 0, "unchecked": 4}
        extra = project / "extra.md"
        extra.write_text("---\ntype: Person\ntitle: Extra\nresource: absent.txt\n---\n")
        mixed = validate_bundle(project, **options)
        assert mixed.outcome == "invalid" and mixed.checks["resources"] == "unavailable"
        assert any(d["code"] == "resource.path" and d["document"] == "extra.md" for d in mixed.diagnostics)
        extra.unlink()
    assert validate_bundle(project, **options).as_dict() == original
    (hidden / "quote.txt").unlink()
    missing = validate_bundle(project, **options)
    assert missing.outcome == "invalid" and missing.checks["resources"] == "failed"


@pytest.mark.parametrize(("name", "check"), [("sub/person.md", "input"), ("index.md", "input"), ("log.md", "logs")])
def test_markdown_requires_utf8(project, name, check):
    path = project / name
    path.parent.mkdir(exist_ok=True)
    path.write_bytes("---\ntype: Person\ntitle: René\n---\n".encode("latin1"))
    report = validate_bundle(project)
    issue, = report.diagnostics
    assert (report.outcome, report.checks[check], issue["code"], issue["document"]) == (
        "invalid", "failed", "document.encoding", name)


def test_authored_event_paths_and_missing_type(project):
    event = "{by: 'human:joe', at: not-a-date, reason: observation}"
    for name, events in [("mapping", event), ("list", f"[{event}]")]:
        (project / f"{name}.md").write_text(f"---\ntype: Person\nverified: {events}\nrefuted: {events}\n---\n")
    (project / "untyped.md").write_text("---\ntitle: Pat\n---\n")
    report = validate_bundle(project)
    assert {(d["document"], d["field"]) for d in report.diagnostics if d["code"] == "schema.format"} == {
        (f"{name}.md", f"/{slot}{index}/at")
        for name, index in [("mapping", ""), ("list", "/0")] for slot in ["verified", "refuted"]}
    assert any(d["document"] == "untyped.md" and d["field"] == "/type" and d["code"] == "schema.required"
               for d in report.diagnostics)


def test_bom_keeps_yaml_source_line(project):
    document = "---\ntype: Person\ntitle: @bad\n---\n"
    for prefix, line in [("", 3), ("\ufeff", 3), ("\ufeff\r\n\r\n", 5)]:
        (project / "pat.md").write_bytes((prefix + document).encode())
        issue, = validate_bundle(project).diagnostics
        assert (issue["document"], issue["line"]) == ("pat.md", line)


def test_domain_union_can_allow_an_untyped_value():
    from jsonschema import Draft7Validator
    from lokf.validation import _field_errors

    schema = {"anyOf": [{"required": ["type"]}, {"required": ["label"]}]}
    error, = Draft7Validator(schema).iter_errors({})
    assert [code for code, _, _ in _field_errors(error, [])] == ["schema.anyOf"]


def test_shacl_shared_subject_attributes_only_unique_assertions(project):
    for name, relation in [("a", "dependsOn: [missing]\n"), ("z", "")]:
        (project / f"{name}.md").write_text(f"---\ntype: Service\nid: https://example.org/kb/shared\n{relation}---\n")
    report = validate_bundle(project, shacl=True)
    assert report.outcome == "invalid" and report.checks["ids"] == "disabled"

    def sources(report):
        return {d["document"] for d in report.diagnostics if d["code"] == "shacl.Class"
                and d["field"] == "http://purl.org/dc/terms/requires"}

    assert sources(report) == {"a.md"}
    (project / "z.md").write_bytes((project / "a.md").read_bytes())
    assert sources(validate_bundle(project, shacl=True)) == {None}


def test_generated_views_are_released_across_schema_edits(project, monkeypatch):
    import gc
    import weakref
    from linkml_runtime.utils.schemaview import SchemaView
    from lokf import shacl, validation
    from lokf.schema_sources import local_view_caches

    views = []

    def observe(view):
        views.append(weakref.ref(view))
        return local_view_caches(view)

    for module in (validation, shacl):
        monkeypatch.setattr(module, "local_view_caches", observe)
    path = project.parent / "course-types.yaml"
    original = path.read_text()
    cache = SchemaView.class_induced_slots.cache_info
    before = cache().currsize
    for revision in range(6):
        path.write_text(original + f"\n# revision {revision}\n")
        assert validate_bundle(project, shacl=True).outcome == "valid"
    gc.collect()
    assert cache().currsize == before
    assert views and all(ref() is None for ref in views)
