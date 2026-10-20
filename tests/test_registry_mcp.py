"""Tests for the ``lokf-registry`` MCP server in ``lokf.registry_mcp`` (SPEC §11.4).

The tools are methods of :class:`RegistryTools`, called directly against a
two-member federation built in a temporary directory; the server wiring is
checked through MCPServer's async introspection, wrapped in ``asyncio.run``.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import zipfile

import pytest

from lokf.registry import Registry, entry_for_archive, entry_for_bundle
from lokf.registry_mcp import RegistryTools, build_server
from lokf.store import GraphStore

A, B = "https://a.example/kb/", "https://b.example/kb/"


def _kb(root: pathlib.Path, base_iri: str, concepts: dict[str, str]) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.md").write_text(f"---\nbase_iri: {base_iri}\ntitle: KB {base_iri}\n---\n# Index\n", encoding="utf-8")
    for name, fm in concepts.items():
        (root / f"{name}.md").write_text(
            f"---\ntype: Concept\ntitle: {name}\ndescription: About {name}.\n{fm}---\n# {name}\n",
            encoding="utf-8",
        )
    return root


@pytest.fixture
def tools(tmp_path):
    a = _kb(tmp_path / "a", A, {"x": f"references:\n  - {B}y\n"})
    b = _kb(tmp_path / "b", B, {"y": "", "z": ""})
    archive = tmp_path / "b.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for f in b.iterdir():
            zf.write(f, f"knowledge/{f.name}")
    reg = Registry(path=tmp_path / "lokf-registry.yaml", title="Test federation")
    reg.add(entry_for_bundle(a))
    reg.add(entry_for_archive(archive, source_base="https://b.example/src"))
    reg.repos[1].distribution = {"archive": str(archive)}  # a local zip, served as a URL would be
    t = RegistryTools(reg, GraphStore.from_registry(reg))
    yield t
    t.close()


def test_five_tools_and_the_index_as_instructions(tools):
    server = build_server(tools)
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert names == {"resolve_iri", "neighbors", "subgraph", "federated_sparql", "read_document"}
    assert "# Test federation" in server.instructions
    assert A in server.instructions and B in server.instructions


def test_resolve_iri_names_the_owner_and_the_concept(tools):
    r = tools.resolve_iri(B + "y")
    assert r["owner"]["base_iri"] == B and r["concept_id"] == "y" and r["via"] == "prefix"
    assert r["concept"]["title"] == "y" and "trust_tier" in r["concept"]["trust"]
    assert tools.resolve_iri("https://elsewhere.example/q")["owner"] is None


def test_neighbors_carry_the_asserting_graph(tools):
    n = tools.neighbors(A + "x")
    edge = [t for t in n["triples"] if t["object"]["value"] == B + "y"]
    assert edge and edge[0]["graph"] == A and not n["truncated"]
    two = tools.neighbors(A + "x", depth=2)
    assert any(t["graph"] == B for t in two["triples"])


def test_neighbors_are_bounded(tools):
    n = tools.neighbors(A + "x", depth=99, limit=1)
    assert n["count"] == 1 and n["truncated"]


def test_subgraph_keeps_graph_names_unless_turtle(tools):
    nq = tools.subgraph([A + "x"], format="nquads")
    assert f"<{A}> ." in nq["rdf"]
    assert "error" in tools.subgraph([A + "x"], format="xml")
    assert tools.subgraph([A + "x"], format="turtle")["count"] == nq["count"]


def test_federated_sparql_binds_the_graph_and_refuses_service(tools):
    r = tools.federated_sparql("SELECT ?g ?s WHERE { GRAPH ?g { ?s a ?t } }", limit=1)
    assert r["columns"] == ["g", "s"] and len(r["rows"]) == 1 and r["truncated"]
    assert tools.federated_sparql("ASK { ?s ?p ?o }") == {"boolean": True}
    refused = tools.federated_sparql("SELECT * WHERE { SERVICE <http://evil/> { ?s ?p ?o } }")
    assert "SERVICE" in refused["error"]


def test_read_document_from_checkout_and_archive(tools):
    assert tools.read_document()["markdown"] == tools.index
    a = tools.read_document(A + "x")
    assert a["read_from"] == "checkout" and a["trust"] is not None
    b = tools.read_document(B + "z")
    assert b["read_from"] == "archive" and b["markdown"].startswith("---")
    assert tools.read_document(B)["path"] == "index.md"
    json.dumps([a, b])  # results go over the wire as JSON


def test_read_document_stays_inside_the_bundle(tools):
    assert "inside its bundle" in tools.read_document(A + "../b/y")["error"]
    assert "error" in tools.read_document("https://elsewhere.example/q")
