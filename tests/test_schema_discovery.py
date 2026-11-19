"""Project discovery and content identity through the shared CLI/MCP surface."""
from __future__ import annotations

import asyncio
import gc
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import weakref

import pytest
from typer.testing import CliRunner
import yaml

from lokf import mcp_server as mcp
from lokf.cli import app
from lokf.schema import (
    _schema_context, _vocabulary, discover_vocabulary, load_context, load_schema,
    schema_context, vocabulary,
)
from lokf.schema_sources import CACHE_SIZE, _cache, capture

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "project"
    p.mkdir()
    shutil.copyfile(ROOT / "lokf.yaml", p / "lokf.yaml")
    (p / "pyproject.toml").write_text('[tool.lokf]\nschema = "domain.yaml"\n')
    (p / "domain.yaml").write_text("""id: https://example.org/root
name: domain
imports: [member]
default_prefix: ex
prefixes:
  ex: https://example.org/
classes:
  SpecialNote:
    is_a: Note
""")
    (p / "member.yaml").write_text("""id: https://example.org/member
name: member
imports: [lokf]
default_prefix: ex
prefixes:
  ex: https://example.org/
classes:
  Issuer:
    is_a: Concept
  Note:
    is_a: Concept
    slots: [aboutIssuer]
slots:
  aboutIssuer:
    range: Issuer
    multivalued: true
    slot_uri: ex:aboutIssuerV1
    description: The issuer discussed by a note.
""")
    b = p / "bundle"
    b.mkdir()
    (b / "index.md").write_text('---\nbase_iri: https://example.org/bundle/\ntitle: Test\n---\n')
    (b / "issuer.md").write_text('---\ntype: Issuer\ntitle: Issuer\n---\n')
    (b / "note.md").write_text('---\ntype: SpecialNote\ntitle: Note\naboutIssuer: [issuer]\n---\n'
                               'Research about [Issuer](issuer.md).\n')
    return p


def revise(path, old="aboutIssuerV1", new="aboutIssuerV2"):
    stat = path.stat()
    path.write_text(path.read_text().replace(old, new))
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))


@pytest.mark.parametrize("cwd", ["neutral", "project"])
def test_discovery_matches_query_and_cli(project, tmp_path, monkeypatch, cwd):
    monkeypatch.chdir(tmp_path if cwd == "neutral" else project)
    args = {"bundle": str(project / "bundle"), "include_metadata": True}
    short = mcp.get_vocabulary(**args)
    full = mcp.get_vocabulary(all=True, **args)
    assert "SpecialNote" in short["classes"]
    rows = {r["name"]: r for r in short["relations"]}
    assert rows["aboutIssuer"]["uri"] == "https://example.org/aboutIssuerV1"
    assert rows["aboutIssuer"]["frontmatter_key"] is True
    assert sum(r["name"] == "aboutIssuer" for r in short["relations"]) == 1
    assert any(s["name"] == "aboutIssuer" for s in full["slots"])
    assert short["schema_metadata"] == full["schema_metadata"]
    assert short["schema_metadata"]["complete"]
    assert mcp.sparql_query(str(project / "bundle"), 'ASK { ?s ex:aboutIssuerV1 ?o }') == {"boolean": True}
    assert "<https://example.org/aboutIssuerV1>" in mcp.convert(str(project / "bundle"), "nt")["rdf"]
    cli = runner.invoke(app, ["vocab", "--bundle", str(project), "--json", "--include-metadata"])
    assert cli.exit_code == 0, cli.output
    assert json.loads(cli.stdout) == {"relations": short["relations"], "schema_metadata": short["schema_metadata"]}
    cli = runner.invoke(app, ["vocab", "--schema", str(project / "domain.yaml"), "--all", "--json", "--include-metadata"])
    assert cli.exit_code == 0, cli.output
    assert json.loads(cli.stdout) == full
    assert mcp.get_vocabulary(bundle=str(project / "bundle/note.md")) == {
        k: v for k, v in short.items() if k != "schema_metadata"}


def test_legacy_calls_and_shapes(project, monkeypatch):
    monkeypatch.chdir(project)
    assert set(mcp.get_vocabulary()) == {"classes", "relations"}
    assert "Note" not in mcp.get_vocabulary()["classes"]
    assert set(mcp.get_vocabulary(True)) == {"schema_version", "classes", "slots", "enums"}
    cli = runner.invoke(app, ["vocab", "--json"])
    assert cli.exit_code == 0
    assert json.loads(cli.stdout) == mcp.get_vocabulary()["relations"]
    cli = runner.invoke(app, ["vocab", "--all", "--json"])
    assert json.loads(cli.stdout) == mcp.get_vocabulary(True)
    cli = runner.invoke(app, ["vocab", "--include-metadata"])
    assert cli.exit_code == 1 and "requires --json" in cli.output


@pytest.mark.parametrize("declaration", ['schema = "missing.yaml"', 'schema = 42', 'schema = ['])
def test_declared_errors_and_override(project, declaration):
    (project / "pyproject.toml").write_text(f"[tool.lokf]\n{declaration}\n")
    for operation in (mcp.get_vocabulary, mcp.propose_relations):
        with pytest.raises((ValueError, FileNotFoundError)):
            operation(bundle=str(project / "bundle"))
    for command in (["vocab", "--bundle", str(project)], ["propose", str(project / "bundle")]):
        result = runner.invoke(app, [*command, "--json"])
        assert result.exit_code == 1
        assert "schema" in result.output.lower() or "pyproject" in result.output
    assert "Note" in mcp.get_vocabulary(bundle=str(project), schema=str(project / "domain.yaml"))["classes"]
    assert mcp.propose_relations(str(project / "bundle"), schema=str(project / "domain.yaml")) == []


def test_malformed_schema_is_error_even_after_warm_cache(project):
    mcp.get_vocabulary(bundle=str(project))
    (project / "member.yaml").write_text("classes: [broken")
    with pytest.raises(yaml.YAMLError):
        mcp.get_vocabulary(bundle=str(project))
    result = runner.invoke(app, ["vocab", "--bundle", str(project), "--json"])
    assert result.exit_code == 1


def test_proposals_recognize_custom_inherited_assertions(project):
    assert mcp.propose_relations(str(project / "bundle")) == []
    result = runner.invoke(app, ["propose", str(project / "bundle"), "--json"])
    assert result.exit_code == 0 and json.loads(result.stdout) == []


def test_source_and_metadata_use_captured_bytes(project):
    root = project / "domain.yaml"
    inputs = capture(root)
    old = inputs.metadata()
    # Change after capture, before parsing/generating the captured interpretation.
    revise(project / "member.yaml")
    assert _vocabulary(inputs).relation_slots["aboutIssuer"].uri.endswith("V1")
    core_data = (ROOT / "lokf.context.jsonld").read_bytes()
    assert _schema_context(inputs, core_data)["aboutIssuer"]["@id"].endswith("V1")
    assert inputs.metadata() == old
    vocab, new = discover_vocabulary(project, include_metadata=True)
    assert vocab.relation_slots["aboutIssuer"].uri.endswith("V2")
    assert new["revision"] != old["revision"]
    assert new["root_sha256"] == old["root_sha256"]
    assert schema_context(root)["aboutIssuer"]["@id"].endswith("V2")
    assert mcp.sparql_query(str(project / "bundle"), 'ASK { ?s ex:aboutIssuerV2 ?o }') == {"boolean": True}


def test_import_removal_never_serves_cached_result(project):
    mcp.get_vocabulary(bundle=str(project))
    schema_context(project / "domain.yaml")
    (project / "member.yaml").unlink()
    for call in (lambda: mcp.get_vocabulary(bundle=str(project)),
                 lambda: schema_context(project / "domain.yaml")):
        with pytest.raises(FileNotFoundError):
            call()


def test_root_and_published_context_edits_are_visible(project, tmp_path):
    root = project / "domain.yaml"
    before = mcp.get_vocabulary(bundle=str(project), include_metadata=True)
    revise(root, "SpecialNote", "AnotherNote")
    after = mcp.get_vocabulary(bundle=str(project), include_metadata=True)
    assert "AnotherNote" in after["classes"] and "SpecialNote" not in after["classes"]
    assert after["schema_metadata"]["revision"] != before["schema_metadata"]["revision"]
    assert "AnotherNote" in load_schema(root)["classes"]
    context = tmp_path / "context.jsonld"
    context.write_text('{"@context": {"@vocab": "https://example.org/v1/"}}')
    assert load_context(context)["@vocab"].endswith("v1/")
    revise(context, "v1", "v2")
    assert load_context(context)["@vocab"].endswith("v2/")


def test_relative_paths_and_portable_identity(project, tmp_path, monkeypatch):
    other = tmp_path / "other"
    shutil.copytree(project, other)
    assert capture(project / "domain.yaml").metadata() == capture(other / "domain.yaml").metadata()
    revise(other / "domain.yaml", "SpecialNote", "AnotherNote")
    for p, expected, absent in ((project, "SpecialNote", "AnotherNote"), (other, "AnotherNote", "SpecialNote")):
        monkeypatch.chdir(p)
        result = vocabulary("domain.yaml")
        assert expected in result.classes and absent not in result.classes


def test_identity_includes_package_types_and_import_contents(project):
    inputs = capture(project / "domain.yaml")
    rows = inputs.metadata()["sources"]
    assert any(r["id"] == "https://w3id.org/linkml/types" for r in rows)
    assert len(rows) == 4
    assert rows == sorted(rows, key=lambda r: (str(r["id"]), r["sha256"]))
    for row in rows:
        assert row["sha256"] in {hashlib.sha256(s.data).hexdigest() for s in inputs.sources}


def test_changed_during_capture_is_rejected(project, monkeypatch):
    original = Path.read_bytes
    changed = False
    def read(path):
        nonlocal changed
        data = original(path)
        if path == project / "member.yaml" and not changed:
            changed = True
            revise(path)
        return data
    monkeypatch.setattr(Path, "read_bytes", read)
    with pytest.raises(ValueError, match="changed while being read"):
        capture(project / "domain.yaml")


def test_local_cycles_and_diamonds_are_finite(project):
    root = project / "domain.yaml"
    content = yaml.safe_load(root.read_text())
    content["imports"] = ["member", "branch"]
    root.write_text(yaml.safe_dump(content))
    (project / "branch.yaml").write_text("id: https://example.org/branch\nname: branch\nimports: [member, domain]\n")
    inputs = capture(root)
    assert len(inputs.sources) == 5
    assert inputs.metadata()["complete"]
    assert "Note" in vocabulary(root).classes


def test_remote_inputs_are_uncached_and_marked_incomplete(project, monkeypatch):
    from lokf import schema
    root = project / "domain.yaml"
    root.write_text("id: https://example.org/remote\nname: remote\nimports: [https://example.org/remote]\n")
    calls = []
    def live(path):
        calls.append(path)
        return deepcopy(load_schema(ROOT / "lokf.yaml"))
    monkeypatch.setattr(schema, "_with_imports", live)
    for _ in range(2):
        result = mcp.get_vocabulary(schema=str(root), include_metadata=True)
        assert result["schema_metadata"]["complete"] is False
        assert result["schema_metadata"]["revision"] is None
    assert len(calls) == 2  # no network used in this test


def test_cache_capacity_and_warm_reuse(project, tmp_path):
    root = project / "domain.yaml"
    assert vocabulary(root) is vocabulary(root)
    for n in range(CACHE_SIZE + 2):
        schema = tmp_path / f"s{n}.yaml"
        schema.write_text(f"id: https://example.org/s{n}\nname: s{n}\n")
        vocabulary(schema)
    assert len(_cache) <= CACHE_SIZE
    assert _vocabulary.cache_info().currsize <= CACHE_SIZE
    assert _schema_context.cache_info().maxsize == CACHE_SIZE


def test_mcp_advertises_optional_selectors():
    tools = asyncio.run(mcp.server.list_tools())
    vocabulary_tool = next(t for t in tools if t.name == "get_vocabulary")
    assert {"all", "bundle", "schema", "include_metadata"} == set(vocabulary_tool.input_schema["properties"])
    assert not vocabulary_tool.input_schema.get("required")


def test_captured_views_are_collectable(project, monkeypatch):
    from lokf import schema_sources
    original = schema_sources._local_caches
    references = []
    def tracked(view):
        references.append(weakref.ref(view))
        return original(view)
    monkeypatch.setattr(schema_sources, "_local_caches", tracked)
    vocabulary(project / "domain.yaml")
    gc.collect()
    assert references and all(ref() is None for ref in references)


def test_symlink_import_retarget_invalidates_capture(project):
    member = project / "member.yaml"
    first, second = project / "first.yaml", project / "second.yaml"
    member.rename(first)
    shutil.copyfile(first, second)
    revise(second)
    member.symlink_to(first.name)
    before = mcp.get_vocabulary(bundle=str(project), include_metadata=True)
    member.unlink()
    member.symlink_to(second.name)
    after = mcp.get_vocabulary(bundle=str(project), include_metadata=True)
    assert before["schema_metadata"]["revision"] != after["schema_metadata"]["revision"]
    assert next(r for r in after["relations"] if r["name"] == "aboutIssuer")["uri"].endswith("V2")


@pytest.mark.parametrize("style", ["is_a", "mixin", "narrowed", "single"])
def test_proposal_domains_follow_inheritance_and_overrides(project, style):
    member = project / "member.yaml"
    data = yaml.safe_load(member.read_text())
    data["classes"]["Note"]["slots"].append("measures")
    data["classes"]["SpecialNote"] = (
        {"mixins": ["Note"], "is_a": "Concept"} if style == "mixin" else {"is_a": "Note"})
    if style == "narrowed":
        data["classes"]["SpecialNote"]["slot_usage"] = {"measures": {"range": "string"}}
    if style == "single":
        data["slots"]["aboutIssuer"]["multivalued"] = False
    member.write_text(yaml.safe_dump(data))
    root = project / "domain.yaml"
    data = yaml.safe_load(root.read_text())
    data.pop("classes")
    root.write_text(yaml.safe_dump(data))
    note = project / "bundle/note.md"
    if style == "single":
        # A single-valued concept reference is already an asserted target too.
        note.write_text(note.read_text().replace("[issuer]", "issuer"))
        assert mcp.propose_relations(str(project / "bundle")) == []
    else:
        note.write_text('---\ntype: SpecialNote\ntitle: Note\n---\nMeasures [Issuer](issuer.md).\n')
        proposals = mcp.propose_relations(str(project / "bundle"))
        assert proposals
        assert (proposals[0]["predicate"] == "measures") == (style != "narrowed")


def test_sibling_import_names_remain_distinct(project):
    for name in ("left", "right"):
        d = project / name
        d.mkdir()
        (d / "schema.yaml").write_text(f"id: https://example.org/{name}\nname: {name}\nimports: [types]\n")
        (d / "types.yaml").write_text(
            f"id: https://example.org/{name}types\nname: {name}types\n"
            f"prefixes:\n  {name}: https://example.org/{name}/\ndefault_prefix: {name}\n"
            f"classes:\n  {name.title()}Thing:\n    class_uri: {name}:Thing\n")
    root = project / "domain.yaml"
    data = yaml.safe_load(root.read_text())
    data["imports"].extend(["left/schema", "right/schema"])
    root.write_text(yaml.safe_dump(data))
    vocab = vocabulary(root)
    ctx = schema_context(root)
    for name in ("left", "right"):
        assert vocab.expand(vocab.classes[f"{name.title()}Thing"]) == f"https://example.org/{name}/Thing"
        assert ctx[f"{name.title()}Thing"]["@id"] == f"{name}:Thing"


def test_live_mcp_refresh_and_project_isolation(project, tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    other = tmp_path / "other"
    shutil.copytree(project, other)
    revise(other / "domain.yaml", "SpecialNote", "AnotherNote")

    async def run():
        params = StdioServerParameters(command=sys.executable, args=["-m", "lokf.mcp_server"], cwd=tmp_path)
        with (tmp_path / "mcp-stderr.log").open("w") as errors:
            async with stdio_client(params, errlog=errors) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=60) as client:
                    await client.initialize()
                    async def call(name, **args):
                        result = await client.call_tool(name, args)
                        assert not result.is_error, result
                        return result.structured_content or json.loads(result.content[0].text)
                    a, b = await asyncio.gather(
                        call("get_vocabulary", bundle=str(project), include_metadata=True),
                        call("get_vocabulary", bundle=str(other), include_metadata=True),
                    )
                    assert "SpecialNote" in a["classes"] and "AnotherNote" not in a["classes"]
                    assert "AnotherNote" in b["classes"] and "SpecialNote" not in b["classes"]
                    old = await call("convert", source=str(project / "bundle"), format="nt")
                    assert "aboutIssuerV1>" in old["rdf"]
                    revise(project / "member.yaml")
                    changed = await call("get_vocabulary", bundle=str(project), include_metadata=True)
                    new = await call("convert", source=str(project / "bundle"), format="nt")
                    assert "aboutIssuerV2>" in new["rdf"] and "aboutIssuerV1>" not in new["rdf"]
                    assert a["schema_metadata"]["revision"] != changed["schema_metadata"]["revision"]
                    (project / "member.yaml").unlink()
                    failed = await client.call_tool("get_vocabulary", {"bundle": str(project)})
                    assert failed.is_error
    asyncio.run(run())


@pytest.mark.parametrize("declaration", ['tool = 42', '[tool]\nlokf = "domain.yaml"'])
def test_invalid_project_tables_do_not_fall_back(project, declaration):
    (project / "pyproject.toml").write_text(declaration)
    for command in (["vocab", "--bundle", str(project)], ["propose", str(project / "bundle"), "--apply"]):
        result = runner.invoke(app, command)
        assert result.exit_code == 1 and "pyproject.toml" in result.output
    with pytest.raises(ValueError, match="pyproject.toml"):
        mcp.get_vocabulary(bundle=str(project))


def test_missing_selector_cannot_discover_an_unrelated_schema(project):
    missing = project / "absent"
    with pytest.raises(FileNotFoundError):
        mcp.get_vocabulary(bundle=str(missing))
    # The explicit override remains usable independently of the discovery anchor.
    assert "Note" in mcp.get_vocabulary(bundle=str(missing), schema=str(project / "domain.yaml"))["classes"]


def test_convert_keeps_the_classes_and_context_from_one_capture(project, monkeypatch):
    from lokf import schema

    root = project / "domain.yaml"
    original = schema._schema_context
    def edit_after_context(*args):
        result = original(*args)
        revise(root, "SpecialNote", "AnotherNote")
        return result

    monkeypatch.setattr(schema, "_schema_context", edit_after_context)
    result = mcp.convert(str(project / "bundle"), "nt")
    assert "<https://example.org/SpecialNote>" in result["rdf"]
    assert "AnotherNote" in mcp.get_vocabulary(bundle=str(project))["classes"]
