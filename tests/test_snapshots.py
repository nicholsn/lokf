"""Read the same Markdown, graph and schema after edits, refreshes and restarts."""
import asyncio
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import zipfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pytest
from typer.testing import CliRunner

from lokf.cli import app
from lokf.registry import Registry, RepoEntry
from lokf.snapshots import SnapshotReader, capture_snapshot

A = "https://example.org/a/"
B = "https://example.org/b/"
QUERY = "SELECT ?g ?title WHERE { GRAPH ?g { ?s schema:name ?title } } ORDER BY ?g"


def bundle(root, base, title):
    root.mkdir(parents=True)
    (root / "index.md").write_text(f"---\nbase_iri: {base}\n---\n")
    (root / "note.md").write_bytes(f"---\r\ntype: Person\r\ntitle: {title}\r\nid: {base}alias\r\n---\r\n".encode())
    return root


def test_registry_revisions_over_stdio(tmp_path):
    a = bundle(tmp_path / "a", A, "v2")
    b = bundle(tmp_path / "b", B, "stable")
    registry = Registry(tmp_path / "registry.yaml", repos=[RepoEntry(A, path="a"), RepoEntry(B, path="b")])
    registry.save()
    store = tmp_path / "captures.sqlite"

    def refresh():
        result = CliRunner().invoke(app, ["snapshot", "capture", str(registry.path), "--store", str(store)])
        assert result.exit_code == 0, result.output
        return json.loads(result.output)

    async def run():
        first = refresh()
        old = first["snapshot"]
        assert refresh() == first
        params = StdioServerParameters(command=sys.executable, args=["-m", "lokf.cli", "snapshot", "mcp", "--store", str(store)])
        async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
            await client.initialize()
            tools = (await client.list_tools()).tools
            assert {t.name for t in tools} == {"get_snapshot", "read_document", "get_vocabulary", "federated_sparql"}
            assert all(t.annotations.read_only_hint for t in tools)

            async def call(name, **args):
                reply = await client.call_tool(name, args)
                assert not reply.is_error, reply.content
                return reply.structured_content

            async def check(expected, title, **pin):
                doc = await call("read_document", iri=A + "alias", member=A, **pin)
                graph = await call("federated_sparql", query=QUERY, **pin)
                assert doc["snapshot"] == graph["snapshot"] == expected["snapshot"]
                assert doc["path"] == "note.md" and f"title: {title}\r\n" in doc["markdown"]
                assert doc["member_revision"] == expected["members"][0]["revision"]
                assert graph["rows"] == [{"g": A, "title": title}, {"g": B, "title": "stable"}]

            (a / "note.md").write_bytes((a / "note.md").read_bytes().replace(b"v2", b"v3"))
            await check(first, "v2")  # The checkout advanced; the captured head did not.
            second = refresh()
            assert first["members"][1] == second["members"][1] and first["members"][0] != second["members"][0]
            await check(second, "v3")
            await check(first, "v2", snapshot=old)
            shutil.rmtree(b)
            with pytest.raises(ValueError, match="Member unavailable"):
                capture_snapshot(registry.path, store)
            assert await call("get_snapshot") == second
            for tool, args in (("get_snapshot", {"snapshot": "unknown"}),
                               ("read_document", {"path": "index.md", "member": "unknown"}),
                               ("federated_sparql", {"query": "ASK {}", "snapshot": "unknown"})):
                result = await client.call_tool(tool, args)
                assert result.is_error and "unavailable" in result.content[0].text.lower()
        # A restarted reader still has both revisions, with the source removed.
        shutil.rmtree(a)
        reader = SnapshotReader(store)
        assert "v2" in reader.read_document("note.md", A, old)["markdown"]
        assert reader.federated_sparql(QUERY)["rows"][0]["title"] == "v3"
    asyncio.run(run())


def test_import_edit_changes_schema_and_graph_without_reinterpreting_old_snapshot(tmp_path):
    kb = bundle(tmp_path / "kb", A, "Pat")
    shutil.copyfile(Path(__file__).resolve().parents[1] / "lokf.yaml", tmp_path / "lokf.yaml")
    (tmp_path / "pyproject.toml").write_text('[tool.lokf]\nschema = "domain.yaml"\n')
    (tmp_path / "domain.yaml").write_text("id: https://example.org/domain\nname: domain\nimports: [types]\n"
                                         "default_prefix: ex\nprefixes: {ex: https://example.org/domain/}\n")
    types = tmp_path / "types.yaml"
    types.write_text("id: https://example.org/types\nname: types\nimports: [lokf]\n"
                     "default_prefix: ex\nprefixes: {ex: https://example.org/domain/}\n"
                     "classes: {Course: {is_a: Concept, class_uri: 'https://example.org/v1/Course'}}\n")
    note = kb / "note.md"
    note.write_bytes(note.read_bytes().replace(b"Person", b"Course"))
    store = tmp_path / "store.sqlite"
    first = capture_snapshot(kb, store)
    types.write_text(types.read_text().replace("v1/", "v2/"))
    second = capture_snapshot(kb, store)
    assert first["members"][0]["schema_revision"] != second["members"][0]["schema_revision"]
    types.unlink()
    reader = SnapshotReader(store)
    for snap, ns in ((first, "v1"), (second, "v2")):
        r = snap["snapshot"]
        schema = reader.get_vocabulary(snapshot=r)
        assert schema["schema_metadata"]["revision"] == snap["members"][0]["schema_revision"]
        assert any(c["name"] == "Course" for c in schema["vocabulary"]["classes"])
        assert reader.federated_sparql(f"ASK {{ ?s a <https://example.org/{ns}/Course> }}", r)["boolean"]
        assert reader.read_document(iri=A + "alias", snapshot=r)["sha256"] == "sha256:" + sha256(note.read_bytes()).hexdigest()


def test_capture_scope_clearance_and_archive(tmp_path, monkeypatch):
    kb = bundle(tmp_path / "source", A, "archive")
    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for p in kb.iterdir():
            zf.write(p, "bundle/" + p.name)
    checksum = "sha256:" + sha256(archive.read_bytes()).hexdigest()
    entry = RepoEntry(A, distribution={"archive": str(archive)}, checksum=checksum, sensitivity="restricted")
    reg = Registry(tmp_path / "registry.yaml", repos=[entry])
    reg.save()
    store = tmp_path / "store.sqlite"
    with pytest.raises(ValueError, match="clearance"):
        capture_snapshot(reg.path, store)
    first = capture_snapshot(reg.path, store, cleared_members=[A])
    with pytest.raises(ValueError, match="scope"):
        capture_snapshot(kb, store)
    # Archive framing also counts towards the size limit on a local copy.
    with monkeypatch.context() as patch:
        patch.setattr("lokf.registry.MAX_ARCHIVE_BYTES", archive.stat().st_size - 1)
        with pytest.raises(ValueError, match="larger than"):
            capture_snapshot(reg.path, store, cleared_members=[A])
    archive.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        capture_snapshot(reg.path, store, cleared_members=[A])
    reader = SnapshotReader(store)
    assert reader.get_snapshot() == first
    assert "archive" in reader.read_document("note.md")["markdown"]


@pytest.mark.parametrize("retarget", [False, True], ids=["edit", "retarget"])
def test_registry_selection_must_survive_capture(tmp_path, monkeypatch, retarget):
    from lokf import snapshots

    a = bundle(tmp_path / "a", A, "before")
    bundle(tmp_path / "b", B, "other")
    child = Registry(tmp_path / "nested.yaml", repos=[RepoEntry(A, path="a")])
    child.save()
    link = tmp_path / "current.yaml"
    link.symlink_to(child.path)
    root = Registry(tmp_path / "root.yaml", repos=[RepoEntry("https://example.org/catalog/", registry=link.name)])
    root.save()
    store = tmp_path / "store.sqlite"
    first = capture_snapshot(root.path, store)
    (a / "note.md").write_bytes((a / "note.md").read_bytes().replace(b"before", b"after"))
    capture_member = snapshots._capture_member

    def edit_registry(*args, **kwargs):
        member = capture_member(*args, **kwargs)
        replacement = Registry(tmp_path / "next.yaml" if retarget else child.path, repos=[RepoEntry(B, path="b")])
        replacement.save()
        if retarget:
            link.unlink()
            link.symlink_to(replacement.path)
        return member

    with monkeypatch.context() as patch:
        patch.setattr(snapshots, "_capture_member", edit_registry)
        with pytest.raises(ValueError, match="Registry changed"):
            capture_snapshot(root.path, store)
    assert SnapshotReader(store).get_snapshot() == first
    assert [m["base_iri"] for m in capture_snapshot(root.path, store)["members"]] == [B]


def test_refresh_is_atomic_for_concurrent_readers(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from lokf import snapshots

    kb = bundle(tmp_path / "source", A, "before")
    store = tmp_path / "snapshots.sqlite"
    first = capture_snapshot(kb, store)
    reader = SnapshotReader(store)
    note = kb / "note.md"
    note.write_bytes(note.read_bytes().replace(b"before", b"after"))
    ready, resume = Event(), Event()
    capture_member = snapshots._capture_member

    def pause_after_insert(*args, **kw):
        member = capture_member(*args, **kw)
        ready.set()
        assert resume.wait(10)
        return member

    monkeypatch.setattr(snapshots, "_capture_member", pause_after_insert)
    with ThreadPoolExecutor(max_workers=1) as pool:
        refresh = pool.submit(capture_snapshot, kb, store)
        try:
            assert ready.wait(10)
            assert reader.get_snapshot() == first
            assert reader.federated_sparql(QUERY)["rows"][0]["title"] == "before"
        finally:
            resume.set()
        second = refresh.result()
    assert reader.get_snapshot() == second
    assert reader.federated_sparql(QUERY)["rows"][0]["title"] == "after"


def test_uncaptured_sources_cannot_advance_the_head(tmp_path):
    kb = bundle(tmp_path / "source", A, "good")
    store = tmp_path / "store.sqlite"
    accepted = capture_snapshot(kb, store)
    evidence = tmp_path / "external.md"
    evidence.write_text("private evidence outside the bundle")
    link = kb / "linked.md"
    link.symlink_to(evidence)
    with pytest.raises(ValueError, match="outside the bundle"):
        capture_snapshot(kb, store)
    link.unlink()
    (tmp_path / "pyproject.toml").write_text('[tool.lokf]\nschema = "domain.yaml"\n')
    (tmp_path / "domain.yaml").write_text("id: https://example.org/domain\nname: domain\n"
                                         "imports: [https://example.org/live]\n")
    with pytest.raises(ValueError, match="not a local file"):
        capture_snapshot(kb, store)
    reader = SnapshotReader(store)
    assert reader.get_snapshot() == accepted
    with pytest.raises(ValueError, match="Document unavailable"):
        reader.read_document("../external.md")


def test_snapshot_store_must_not_overwrite_capture_inputs(tmp_path):
    manifest = tmp_path / "registry.yaml"
    manifest.touch()
    store = tmp_path / "store.sqlite"
    store.hardlink_to(manifest)
    with pytest.raises(ValueError, match="overlap"):
        capture_snapshot(manifest, store)
    assert manifest.read_bytes() == b""

    kb = bundle(tmp_path / "source", A, "before")
    reg = Registry(manifest, repos=[RepoEntry(A, path=str(kb))])
    nested = tmp_path / "nested.yaml"
    reg.repos.append(RepoEntry(B, registry=nested.name))
    reg.save()
    with pytest.raises(ValueError, match="overlap"):
        capture_snapshot(manifest, nested)
    assert not nested.exists()
    nested.touch()
    with pytest.raises(ValueError, match="overlap"):
        capture_snapshot(manifest, nested)
    assert nested.read_bytes() == b""
    for source in (kb, manifest):
        with pytest.raises(ValueError, match="overlap"):
            capture_snapshot(source, kb / "new.md")
        assert not (kb / "new.md").exists()
    store.unlink()
    (kb / "log.md").touch()
    store.hardlink_to(kb / "log.md")
    with pytest.raises(ValueError, match="overlap"):
        capture_snapshot(kb, store)
    assert (kb / "log.md").read_bytes() == b""


def test_graph_subjects_resolve_and_unqueryable_capture_preserves_empty_head(tmp_path):
    kb = bundle(tmp_path / "source", A, "data")
    store = tmp_path / "store.sqlite"
    note = kb / "note.md"
    for authored, expanded in (("relative", A + "relative"), ("schema:Thing", "http://schema.org/Thing")):
        note.write_text(f"---\ntype: Person\nid: {authored}\n---\n")
        capture_snapshot(kb, store)
        reader = SnapshotReader(store)
        assert reader.federated_sparql("SELECT ?s WHERE { ?s a schema:Person }")["rows"] == [{"s": expanded}]
        assert reader.read_document(iri=expanded) == reader.read_document(iri=authored)
    # Stores from before expanded-IRI lookup can still read the original pin.
    original = reader.get_snapshot()
    with sqlite3.connect(store) as db:
        db.execute("DROP TABLE document_aliases")
    assert reader.read_document(iri=authored, snapshot=original["snapshot"])["path"] == "note.md"
    assert capture_snapshot(kb, store) == original
    assert reader.read_document(iri=expanded, snapshot=original["snapshot"])["path"] == "note.md"
    (kb / "other.md").write_text(f"---\ntype: Person\nid: {expanded}\n---\n")
    capture_snapshot(kb, store)
    with pytest.raises(ValueError, match="Multiple documents"):
        reader.read_document(iri=expanded)
    (kb / "other.md").unlink()
    note.unlink()
    head = capture_snapshot(kb, store)
    assert reader.federated_sparql("SELECT ?g WHERE { GRAPH ?g {} }")["rows"] == [{"g": A}]
    note.write_text(f"---\ntype: Person\nid: {A}bad%XX\n---\n")
    with pytest.raises(ValueError, match="cannot be queried"):
        capture_snapshot(kb, store)
    assert reader.get_snapshot() == head


def test_reader_reports_inconsistent_retained_digests(tmp_path):
    kb = bundle(tmp_path / "source", A, "data")
    store = tmp_path / "store.sqlite"
    receipt = capture_snapshot(kb, store)
    reader = SnapshotReader(store)
    doc = reader.read_document("note.md")
    expected_vocab = reader.get_vocabulary()
    with sqlite3.connect(store) as db:
        db.execute("UPDATE blobs SET markdown=? WHERE digest=?", (b"damaged", doc["sha256"]))
    with pytest.raises(ValueError, match="Markdown digest mismatch"):
        reader.read_document("note.md")
    with sqlite3.connect(store) as db:
        db.execute("UPDATE snapshots SET manifest='{}' WHERE revision=?", (receipt["snapshot"],))
    with pytest.raises(ValueError, match="manifest digest mismatch"):
        reader.federated_sparql("ASK {}")
    with pytest.raises(ValueError, match="manifest digest mismatch"):
        reader.read_document("index.md")
    with sqlite3.connect(store) as db:
        db.execute("DELETE FROM documents WHERE path='index.md'")
        db.execute("UPDATE members SET vocabulary='{}', graph=x''")
    assert capture_snapshot(kb, store) == receipt
    assert reader.read_document("note.md") == doc
    assert reader.read_document("index.md")["path"] == "index.md"
    assert reader.get_vocabulary() == expected_vocab
    assert reader.federated_sparql(QUERY)["rows"] == [{"g": A, "title": "data"}]
