"""Tests for the cross-bundle registry (meta-lokf) — SPEC §11.

Covers the offline Phase 1 engine: longest-``base_iri``-prefix routing, the
explicit-``id`` fallback, the registration guards, entry building from a local
bundle, and the ``lokf registry`` CLI round-trip.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import zipfile

import pytest
import yaml
from typer.testing import CliRunner

from lokf.cli import app
from lokf.registry import (
    VOCAB_NS,
    RepoEntry,
    Registry,
    entry_for_archive,
    entry_for_bundle,
    load_registry,
)

runner = CliRunner()
BUNDLE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge"


def _reg(*bases: str) -> Registry:
    """A registry built directly from base_iris (bypassing add() guards)."""
    return Registry(
        path=pathlib.Path("x"),
        repos=[RepoEntry(base_iri=b, title=b, source_base=b) for b in bases],
    )


# -- routing ----------------------------------------------------------------
def test_owner_longest_prefix_wins():
    """The owner is the longest base_iri that prefixes the IRI, even when nested."""
    reg = _reg("https://ex.org/", "https://ex.org/sub/")
    assert reg.owner("https://ex.org/sub/x").base_iri == "https://ex.org/sub/"
    assert reg.owner("https://ex.org/top").base_iri == "https://ex.org/"


def test_resolve_prefix_gives_concept_id_and_source_url():
    reg = _reg("https://acme.example/knowledge/")
    res = reg.resolve("https://acme.example/knowledge/tables/user-events")
    assert res.via == "prefix" and not res.external
    assert res.concept_id == "tables/user-events"
    assert res.source_url == "https://acme.example/knowledge/tables/user-events.md"


def test_resolve_external_is_tolerated_not_error():
    res = _reg("https://acme.example/knowledge/").resolve("https://other.example/x")
    assert res.external and res.entry is None and res.concept_id is None


def test_id_index_fallback_routes_diverging_ids():
    """An explicit id outside base_iri still routes via the id_index."""
    reg = Registry(
        path=pathlib.Path("x"),
        repos=[
            RepoEntry(
                base_iri="https://ex.org/kb/",
                source_base="https://ex.org/kb/",
                id_index={"https://ex.org/legacy/wau": "metrics/wau"},
            )
        ],
    )
    res = reg.resolve("https://ex.org/legacy/wau")
    assert res.via == "id_index" and res.concept_id == "metrics/wau"
    assert res.source_url == "https://ex.org/kb/metrics/wau.md"


# -- registration guards ----------------------------------------------------
def test_add_rejects_vocab_namespace():
    reg = Registry(path=pathlib.Path("x"))
    with pytest.raises(ValueError, match="vocabulary namespace"):
        reg.add(RepoEntry(base_iri=VOCAB_NS))


def test_add_rejects_duplicate_and_nesting():
    reg = Registry(path=pathlib.Path("x"))
    reg.add(RepoEntry(base_iri="https://ex.org/a/"))
    with pytest.raises(ValueError, match="already registered"):
        reg.add(RepoEntry(base_iri="https://ex.org/a/"))
    with pytest.raises(ValueError, match="nest"):
        reg.add(RepoEntry(base_iri="https://ex.org/a/sub/"))
    with pytest.raises(ValueError, match="nest"):
        reg.add(RepoEntry(base_iri="https://ex.org/"))


def test_add_rejects_empty_base_iri():
    with pytest.raises(ValueError, match="no base_iri"):
        Registry(path=pathlib.Path("x")).add(RepoEntry(base_iri=""))


# -- entry building from a bundle -------------------------------------------
def test_entry_for_bundle_indexes_the_example():
    entry = entry_for_bundle(BUNDLE, source_base="https://x/")
    assert entry.base_iri == "https://acme.example/knowledge/"
    assert entry.void["triples"] == 157
    # Six concepts, each a distinct type; all route by prefix, so id_index empty.
    assert sum(entry.void["class_partition"].values()) == 8
    assert entry.id_index == {}


def _write_bundle(root: pathlib.Path, base_iri: str, concept: str, explicit_id: str | None):
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.md").write_text(f"---\nbase_iri: {base_iri}\ntitle: T\n---\n", encoding="utf-8")
    fm = f"id: {explicit_id}\n" if explicit_id else ""
    (root / f"{concept}.md").write_text(
        f"---\n{fm}type: Concept\ntitle: Thing\n---\nbody\n", encoding="utf-8"
    )


def test_entry_for_bundle_harvests_diverging_explicit_id(tmp_path):
    """A concept whose explicit id escapes base_iri lands in id_index when allowed."""
    root = tmp_path / "kb"
    _write_bundle(root, "https://ex.org/kb/", "legacy", "https://ex.org/legacy/thing")
    entry = entry_for_bundle(root, allow_foreign_ids=True)
    assert entry.id_index == {"https://ex.org/legacy/thing": "legacy"}


def test_entry_for_bundle_refuses_foreign_id_by_default(tmp_path):
    """SPEC §11.3 rule 3: an id outside base_iri is refused unless declared."""
    root = tmp_path / "kb"
    _write_bundle(root, "https://a.example/knowledge/", "x", "https://elsewhere.example/x")
    with pytest.raises(ValueError, match="outside base_iri"):
        entry_for_bundle(root)


def test_entry_for_bundle_records_the_absolute_path(tmp_path):
    """A directory stays loadable with or without --source-base."""
    assert entry_for_bundle(BUNDLE, source_base="https://x/").path == str(BUNDLE)
    assert entry_for_bundle(BUNDLE).path == str(BUNDLE)


def test_cli_add_writes_local_locations_relative_to_the_manifest(tmp_path):
    """A manifest built on a CI runner reads the same in any checkout."""
    archive = _zip_bundle(tmp_path)

    def added(*args) -> dict:
        manifest = tmp_path / "fed" / f"r{len(list(tmp_path.glob('fed/*.yaml')))}.yaml"
        runner.invoke(app, ["registry", "init", "-r", str(manifest)])
        r = runner.invoke(app, ["registry", "add", *args, "-r", str(manifest)])
        assert r.exit_code == 0, r.output
        return yaml.safe_load(manifest.read_text())["repos"][0]

    raw = added(str(BUNDLE), "--source-base", "https://x/")
    assert raw["path"] == pathlib.Path(os.path.relpath(BUNDLE, tmp_path / "fed")).as_posix()
    assert added(str(archive))["distribution"] == {"archive": "../knowledge-v1.zip"}
    url = "https://releases.example/knowledge-v1.zip"
    raw = added(str(archive), "--archive-url", url)
    assert raw["distribution"] == {"archive": url} and "path" not in raw


def test_cli_add_refuses_archive_url_for_a_directory(tmp_path):
    manifest = tmp_path / "lokf-registry.yaml"
    runner.invoke(app, ["registry", "init", "-r", str(manifest)])
    r = runner.invoke(app, ["registry", "add", str(BUNDLE), "--archive-url", "https://x/k.zip", "-r", str(manifest)])
    assert r.exit_code == 1 and "apply to a zip" in r.output


def test_add_refuses_id_in_another_members_namespace():
    reg = Registry(path=pathlib.Path("x"))
    reg.add(RepoEntry(base_iri="https://a.example/"))
    with pytest.raises(ValueError, match="lies in registered"):
        reg.add(RepoEntry(base_iri="https://b.example/", id_index={"https://a.example/x": "x"}))


def test_add_refuses_base_iri_capturing_an_indexed_id():
    reg = Registry(path=pathlib.Path("x"))
    reg.add(RepoEntry(base_iri="https://b.example/", id_index={"https://a.example/x": "x"}))
    with pytest.raises(ValueError, match="captures explicit id"):
        reg.add(RepoEntry(base_iri="https://a.example/"))


# -- entry building from a release zip ---------------------------------------
def _zip_bundle(tmp_path: pathlib.Path, top: str = "knowledge") -> pathlib.Path:
    """The example bundle zipped under *top*/, as a KTL release ships it."""
    archive = tmp_path / "knowledge-v1.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for f in BUNDLE.rglob("*"):
            if f.is_file():
                zf.write(f, f"{top}/{f.relative_to(BUNDLE)}" if top else str(f.relative_to(BUNDLE)))
    return archive


def _digest(path: pathlib.Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("top", ["knowledge", ""])
def test_entry_for_archive_unpacks_and_records_checksum(tmp_path, top):
    archive = _zip_bundle(tmp_path, top)
    entry = entry_for_archive(archive, source_base="https://x/", checksum=_digest(archive))
    assert entry.base_iri == "https://acme.example/knowledge/"
    assert entry.void["triples"] == 157
    assert entry.checksum == _digest(archive)
    assert entry.path is None and entry.source_base == "https://x/"
    assert entry.distribution == {"archive": str(archive.resolve())}


def test_entry_for_archive_without_source_base_has_no_runner_path(tmp_path):
    entry = entry_for_archive(_zip_bundle(tmp_path))
    assert entry.path is None and entry.source_base == ""


def test_entry_for_archive_refuses_checksum_mismatch(tmp_path):
    with pytest.raises(ValueError, match="checksum mismatch"):
        entry_for_archive(_zip_bundle(tmp_path), checksum="0" * 64)


def test_entry_for_archive_refuses_unsafe_member(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.md", "x")
    with pytest.raises(ValueError, match="unsafe member"):
        entry_for_archive(archive)


def test_entry_for_archive_from_url_records_distribution(tmp_path, monkeypatch):
    archive = _zip_bundle(tmp_path)
    monkeypatch.setattr("lokf.registry._download", lambda url, dest, **kw: shutil.copy(archive, dest))
    url = "https://example.org/releases/knowledge-v1.zip"
    entry = entry_for_archive(url)
    assert entry.distribution == {"archive": url}
    assert entry.checksum == _digest(archive)


# -- CLI round-trip ---------------------------------------------------------
def test_cli_init_add_list_resolve(tmp_path):
    manifest = tmp_path / "lokf-registry.yaml"
    assert runner.invoke(app, ["registry", "init", "-r", str(manifest)]).exit_code == 0
    assert manifest.exists()

    add = runner.invoke(
        app,
        ["registry", "add", str(BUNDLE), "-r", str(manifest), "--source-base", "https://x/"],
    )
    assert add.exit_code == 0 and "157 triples" in add.output

    listed = runner.invoke(app, ["registry", "list", "-r", str(manifest)])
    assert "https://acme.example/knowledge/" in listed.output

    ok = runner.invoke(
        app,
        ["registry", "resolve", "https://acme.example/knowledge/glossary/active-user",
         "-r", str(manifest)],
    )
    assert ok.exit_code == 0
    assert "concept_id: glossary/active-user" in ok.output
    assert "source_url: https://x/glossary/active-user.md" in ok.output

    external = runner.invoke(
        app, ["registry", "resolve", "https://nope.example/x", "-r", str(manifest)]
    )
    assert external.exit_code == 1 and "external" in external.output


def test_cli_add_rejects_second_copy_of_same_bundle(tmp_path):
    """Registering the same base_iri twice is a clean error, not a traceback."""
    manifest = tmp_path / "lokf-registry.yaml"
    runner.invoke(app, ["registry", "init", "-r", str(manifest)])
    runner.invoke(app, ["registry", "add", str(BUNDLE), "-r", str(manifest)])
    again = runner.invoke(app, ["registry", "add", str(BUNDLE), "-r", str(manifest)])
    assert again.exit_code == 1 and "already registered" in again.output


def test_cli_add_registers_a_zip(tmp_path):
    manifest = tmp_path / "lokf-registry.yaml"
    runner.invoke(app, ["registry", "init", "-r", str(manifest)])
    archive = _zip_bundle(tmp_path)
    add = runner.invoke(app, ["registry", "add", str(archive), "-r", str(manifest)])
    assert add.exit_code == 0, add.output
    raw = yaml.safe_load(manifest.read_text())["repos"][0]
    assert raw["checksum"] == _digest(archive) and "path" not in raw


def test_cli_add_reports_foreign_ids_when_allowed(tmp_path):
    manifest = tmp_path / "lokf-registry.yaml"
    runner.invoke(app, ["registry", "init", "-r", str(manifest)])
    root = tmp_path / "kb"
    _write_bundle(root, "https://a.example/knowledge/", "x", "https://elsewhere.example/x")
    refused = runner.invoke(app, ["registry", "add", str(root), "-r", str(manifest)])
    assert refused.exit_code == 1 and "outside base_iri" in refused.output
    allowed = runner.invoke(
        app, ["registry", "add", str(root), "-r", str(manifest), "--allow-foreign-ids"]
    )
    assert allowed.exit_code == 0 and "1 explicit id(s) outside base_iri" in allowed.output


def test_cli_list_missing_manifest_is_clean_error(tmp_path):
    r = runner.invoke(app, ["registry", "list", "-r", str(tmp_path / "nope.yaml")])
    assert r.exit_code == 1 and "not found" in r.output


@pytest.mark.parametrize("text", ["repos: [\n", "- a list\n"])
def test_cli_reports_a_malformed_manifest_cleanly(tmp_path, text):
    manifest = tmp_path / "lokf-registry.yaml"
    manifest.write_text(text, encoding="utf-8")
    for args in (["list"], ["resolve", "https://x/"], ["add", str(BUNDLE)]):
        r = runner.invoke(app, ["registry", *args, "-r", str(manifest)])
        assert r.exit_code == 1 and "cannot read the registry" in r.output, args
        assert r.exception is None or isinstance(r.exception, SystemExit), args


def test_cli_init_creates_parent_dirs(tmp_path):
    manifest = tmp_path / "nested" / "dir" / "lokf-registry.yaml"
    assert runner.invoke(app, ["registry", "init", "-r", str(manifest)]).exit_code == 0
    assert manifest.exists()


# -- robustness / boundary regressions (from the Phase 1 review) -------------
def test_add_requires_trailing_separator():
    reg = Registry(path=pathlib.Path("x"))
    with pytest.raises(ValueError, match="end with"):
        reg.add(RepoEntry(base_iri="https://ex.org/team"))
    reg.add(RepoEntry(base_iri="https://ex.org/team/"))  # slash ok
    reg.add(RepoEntry(base_iri="https://ex.org/onto#"))  # hash ok


def test_sibling_namespaces_register_and_route():
    """`…/team/` and `…/team-archive/` don't nest and never cross-route."""
    reg = Registry(path=pathlib.Path("x"))
    reg.add(RepoEntry(base_iri="https://ex.org/team/"))
    reg.add(RepoEntry(base_iri="https://ex.org/team-archive/"))  # not a nesting conflict
    assert reg.owner("https://ex.org/team-archive/r").base_iri == "https://ex.org/team-archive/"
    assert reg.owner("https://ex.org/team/r").base_iri == "https://ex.org/team/"


def test_add_rejects_vocab_ancestor():
    reg = Registry(path=pathlib.Path("x"))
    with pytest.raises(ValueError, match="vocabulary namespace"):
        reg.add(RepoEntry(base_iri="https://w3id.org/"))


def test_resolve_bare_base_iri_has_no_document_url():
    """The namespace root is owned but is not a concept — no bogus .md URL."""
    res = _reg("https://ex.org/kb/").resolve("https://ex.org/kb/")
    assert not res.external and res.concept_id == "" and res.source_url is None


def test_prefix_beats_stale_id_index():
    """A more-specific prefix owner wins over another repo's id_index entry."""
    reg = Registry(
        path=pathlib.Path("x"),
        repos=[
            RepoEntry(base_iri="https://ex.org/kb/", source_base="https://ex.org/kb/"),
            RepoEntry(base_iri="https://other.org/", id_index={"https://ex.org/kb/x": "hijack"}),
        ],
    )
    res = reg.resolve("https://ex.org/kb/x")
    assert res.via == "prefix" and res.concept_id == "x"
    assert res.entry.base_iri == "https://ex.org/kb/"


def test_own_id_index_names_the_concept_under_base_iri(tmp_path):
    """An explicit id under base_iri that differs from the file path routes to
    the concept that declares it, not to a document named after the IRI."""
    root = tmp_path / "kb"
    _write_bundle(root, "https://ex.org/kb/", "legacy", "https://ex.org/kb/old/thing")
    reg = Registry(path=pathlib.Path("x"))
    reg.add(entry_for_bundle(root, source_base="https://src/"))
    res = reg.resolve("https://ex.org/kb/old/thing")
    assert res.via == "id_index" and res.concept_id == "legacy"
    assert res.source_url == "https://src/legacy.md"


def test_load_registry_tolerates_null_fields(tmp_path):
    """A hand-edited manifest with null id_index/void/repos doesn't crash lookups."""
    manifest = tmp_path / "r.yaml"
    manifest.write_text(
        "lokf_registry_version: '0.1'\nrepos:\n"
        "  - base_iri: https://ex.org/kb/\n    id_index:\n    void:\n",
        encoding="utf-8",
    )
    reg = load_registry(manifest)
    assert reg.repos[0].id_index == {} and reg.repos[0].void == {}
    assert reg.owner("https://ex.org/kb/thing").base_iri == "https://ex.org/kb/"
    assert reg.resolve("https://nope.org/x").external


def test_load_registry_tolerates_null_repos(tmp_path):
    manifest = tmp_path / "r.yaml"
    manifest.write_text("lokf_registry_version: '0.1'\nrepos:\n", encoding="utf-8")
    assert load_registry(manifest).repos == []


def test_load_registry_round_trips(tmp_path):
    manifest = tmp_path / "lokf-registry.yaml"
    reg = Registry(path=manifest, id="https://w3id.org/lokf/registry/x", title="X")
    reg.add(entry_for_bundle(BUNDLE, source_base="https://x/"))
    reg.save()

    reloaded = load_registry(manifest)
    assert reloaded.id == "https://w3id.org/lokf/registry/x"
    assert len(reloaded.repos) == 1
    assert reloaded.repos[0].base_iri == "https://acme.example/knowledge/"
    # the on-disk form drops empty fields
    raw = yaml.safe_load(manifest.read_text())
    assert "id_index" not in raw["repos"][0]


def test_entry_for_archive_refuses_too_many_entries(tmp_path, monkeypatch):
    monkeypatch.setattr("lokf.registry.MAX_ARCHIVE_ENTRIES", 3)
    with pytest.raises(ValueError, match="more than 3"):
        entry_for_archive(_zip_bundle(tmp_path))


# -- downloads and unpacking ---------------------------------------------------
@pytest.fixture
def http_files(tmp_path):
    """A local HTTP server over tmp_path/www; yields its base URL."""
    import functools
    import http.server
    import threading

    www = tmp_path / "www"
    www.mkdir()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(www))
    handler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", www
    srv.shutdown()


def test_entry_for_archive_downloads_for_real(tmp_path, http_files):
    base, www = http_files
    archive = _zip_bundle(tmp_path)
    shutil.copy(archive, www / "k.zip")
    entry = entry_for_archive(f"{base}/k.zip")
    assert entry.checksum == _digest(archive) and entry.distribution == {"archive": f"{base}/k.zip"}
    with pytest.raises(OSError):
        entry_for_archive(f"{base}/missing.zip")


def test_download_over_the_cap_leaves_no_file(tmp_path, http_files, monkeypatch):
    from lokf.registry import _download

    base, www = http_files
    (www / "big.zip").write_bytes(b"x" * 4096)
    dest = tmp_path / "out.zip"
    with pytest.raises(ValueError, match="larger than 1024"):
        _download(f"{base}/big.zip", dest, max_bytes=1024)
    assert not dest.exists()


def test_redirects_refuse_downgrades_and_the_local_network():
    import urllib.error
    import urllib.request

    from lokf.registry import _Redirects

    req = urllib.request.Request("https://releases.example/k.zip")
    with pytest.raises(urllib.error.URLError, match="refused redirect from"):
        _Redirects(local_ok=False).redirect_request(req, None, 302, "Found", {}, "http://cdn.example/k.zip")
    with pytest.raises(urllib.error.URLError, match="local network"):
        _Redirects(local_ok=False).redirect_request(req, None, 302, "Found", {}, "https://127.0.0.1/admin")
    with pytest.raises(urllib.error.URLError):
        _Redirects(local_ok=True).redirect_request(req, None, 302, "Found", {}, "file:///etc/passwd")


def test_a_corrupt_zip_is_a_clean_error(tmp_path):
    archive = _zip_bundle(tmp_path)
    data = bytearray(archive.read_bytes())
    i = data.index(b"base_iri")  # inside index.md's stored bytes
    data[i:i + 8] = b"BASE_IRI"  # same length, wrong CRC
    archive.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="cannot be unpacked"):
        entry_for_archive(archive)


def test_an_absolute_member_path_is_refused(tmp_path):
    archive = tmp_path / "abs.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("/etc/evil.md", "x")
    with pytest.raises(ValueError, match="unsafe member"):
        entry_for_archive(archive)


@pytest.mark.parametrize("entry,message", [
    ("- base_iri: [https://a/]\n", "has no base_iri"),
    ("- title: no base\n", "has no base_iri"),
    ("- just a string\n", "must be a mapping"),
    ("- base_iri: https://a/\n  distribution: https://a/graph.nt\n", "distribution must be a dict"),
    ("- base_iri: https://a/\n  title: [a, b]\n", "title must be a str"),
    ("- base_iri: https://a/\n  checksum: md5:abc\n", "checksum must be"),
])
def test_load_registry_names_a_malformed_entry(tmp_path, entry, message):
    manifest = tmp_path / "r.yaml"
    manifest.write_text("repos:\n" + entry, encoding="utf-8")
    with pytest.raises(ValueError, match=f"repos\\\\[0\\\\].*{message}|{message}"):
        load_registry(manifest)


def test_load_registry_normalises_a_hand_written_checksum(tmp_path):
    manifest = tmp_path / "r.yaml"
    manifest.write_text("repos:\n- base_iri: https://a/\n  checksum: " + "AB" * 32 + "\n", encoding="utf-8")
    assert load_registry(manifest).repos[0].checksum == "sha256:" + "ab" * 32


def test_add_refuses_an_id_two_members_index():
    reg = Registry(path=pathlib.Path("x"))
    reg.add(RepoEntry(base_iri="https://a.example/", id_index={"https://legacy.example/x": "x"}))
    with pytest.raises(ValueError, match="already indexed by"):
        reg.add(RepoEntry(base_iri="https://b.example/", id_index={"https://legacy.example/x": "y"}))


def test_an_id_in_the_entrys_own_namespace_under_the_vocabulary_is_allowed():
    reg = Registry(path=pathlib.Path("x"))
    own = VOCAB_NS + "examples/"
    reg.add(RepoEntry(base_iri=own, id_index={own + "old/x": "x"}))
    assert len(reg.repos) == 1
    with pytest.raises(ValueError, match="vocabulary namespace"):
        reg.add(RepoEntry(base_iri="https://b.example/", id_index={VOCAB_NS + "Metric": "m"}))


# -- federated store (SPEC §11.4) -------------------------------------------
def _kb(root: pathlib.Path, base_iri: str, concepts: dict[str, str]) -> pathlib.Path:
    """A bundle at *root* whose concepts are given as frontmatter bodies."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.md").write_text(f"---\nbase_iri: {base_iri}\ntitle: T\n---\n", encoding="utf-8")
    for name, fm in concepts.items():
        (root / f"{name}.md").write_text(f"---\ntype: Concept\ntitle: {name}\n{fm}---\n", encoding="utf-8")
    return root


SOURCE = "sources:\n  - title: S\n    url: https://s.example/doc\n"


def _federation(tmp_path) -> Registry:
    a = _kb(tmp_path / "a", "https://a.example/kb/", {
        "x": SOURCE + "references:\n"
        "  - https://b.example/kb/y\n"
        "  - https://b.example/kb/nope\n"
        "  - https://c.example/z\n",
    })
    b = _kb(tmp_path / "b", "https://b.example/kb/", {"y": SOURCE})
    reg = Registry(path=tmp_path / "lokf-registry.yaml")
    reg.add(entry_for_bundle(a))
    reg.add(entry_for_bundle(b))
    return reg


def test_from_registry_loads_one_named_graph_per_member(tmp_path):
    from lokf.store import GraphStore

    reg = _federation(tmp_path)
    store = GraphStore.from_registry(reg)
    rows = store.select("SELECT ?g (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g")
    graphs = {r["g"]: int(r["n"]) for r in rows}
    assert set(graphs) == {"https://a.example/kb/", "https://b.example/kb/"}
    # The union default graph holds both, and the members' blank nodes stay apart.
    union = store.select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")[0]["n"]
    assert int(union) == sum(graphs.values())
    assert len(store.rdflib_graph()) == int(union)


def test_from_registry_skips_an_unloadable_member(tmp_path):
    from lokf.store import GraphStore

    reg = _federation(tmp_path)
    reg.repos.append(RepoEntry(base_iri="https://gone.example/"))
    store = GraphStore.from_registry(reg)
    assert set(store.load_errors) == {"https://gone.example/"}
    assert len(store) > 0


def test_unresolved_targets_names_unowned_and_missing(tmp_path):
    from lokf.registry import unresolved_targets
    from lokf.store import GraphStore

    reg = _federation(tmp_path)
    found = {(u.target, u.kind) for u in unresolved_targets(reg, GraphStore.from_registry(reg))}
    assert found == {
        ("https://b.example/kb/nope", "missing"),
        ("https://c.example/z", "unowned"),
    }


def test_cli_registry_build_and_query(tmp_path):
    reg = _federation(tmp_path)
    reg.save()
    manifest, out = str(reg.path), tmp_path / "fed"
    built = runner.invoke(app, ["registry", "build", "-r", manifest, "-d", str(out)])
    assert built.exit_code == 0, built.output
    assert "2 of 2 members" in built.output
    assert "unowned: https://c.example/z" in built.output
    assert "missing: https://b.example/kb/nope" in built.output
    strict = runner.invoke(app, ["registry", "build", "-r", manifest, "-d", str(out), "--strict"])
    assert strict.exit_code == 1

    q = runner.invoke(app, [
        "registry", "query", "--quads", str(out / "federation.nq"),
        "SELECT ?g WHERE { GRAPH ?g { <https://b.example/kb/y> ?p ?o } } LIMIT 1",
    ])
    assert q.exit_code == 0 and "https://b.example/kb/" in q.output


def test_from_registry_skips_a_member_whose_content_fails(tmp_path):
    """Broken frontmatter in one member, or a malformed graph.nt, is that
    member's failure alone; nothing of it reaches the store."""
    from lokf.store import GraphStore

    reg = _federation(tmp_path)
    (tmp_path / "b" / "z.md").write_text("---\ntype: Concept\ntitle: [unclosed\n---\n", encoding="utf-8")
    bad_nt = tmp_path / "graph.nt"
    bad_nt.write_text("<https://c.example/kb/x> <http://p> .\n", encoding="utf-8")
    reg.repos.append(RepoEntry(base_iri="https://c.example/kb/", distribution={"rdf": str(bad_nt)}))
    store = GraphStore.from_registry(reg)
    assert set(store.load_errors) == {"https://b.example/kb/", "https://c.example/kb/"}
    graphs = {r["g"] for r in store.select("SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }")}
    assert graphs == {"https://a.example/kb/"}


def test_unresolved_targets_skip_vocabulary_terms_and_unloaded_owners(tmp_path):
    from lokf.registry import unresolved_targets
    from lokf.store import GraphStore

    a = _kb(tmp_path / "a", "https://a.example/kb/", {
        "x": "references:\n  - https://w3id.org/lokf/Metric\n  - https://b.example/kb/y\n",
    })
    reg = Registry(path=tmp_path / "r.yaml")
    reg.add(entry_for_bundle(a))
    reg.add(RepoEntry(base_iri="https://b.example/kb/"))  # nothing to load it from
    store = GraphStore.from_registry(reg)
    assert "https://b.example/kb/" in store.load_errors
    assert unresolved_targets(reg, store) == []


def test_from_and_from_named_are_not_overridden_by_the_union(tmp_path):
    from lokf.store import GraphStore

    store = GraphStore.from_registry(_federation(tmp_path))
    one = "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }"
    union = int(store.select(one)[0]["n"])
    only_a = int(store.select(one.replace("WHERE", "FROM <https://a.example/kb/> WHERE"))[0]["n"])
    assert 0 < only_a < union
    named = "SELECT (COUNT(*) AS ?n) FROM NAMED <https://a.example/kb/> WHERE { ?s ?p ?o }"
    assert int(store.select(named)[0]["n"]) == 0  # FROM NAMED alone: an empty default graph


def test_relative_locations_are_read_against_the_manifest(tmp_path, monkeypatch):
    from lokf.store import GraphStore

    root = tmp_path / "fed"
    _kb(root / "a", "https://a.example/kb/", {"x": ""})
    manifest = root / "lokf-registry.yaml"
    manifest.write_text("repos:\n- base_iri: https://a.example/kb/\n  path: a\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # anywhere but beside the manifest
    store = GraphStore.from_registry(manifest)
    assert store.load_errors == {} and len(store) > 0


def test_registry_build_is_byte_stable_across_processes(tmp_path):
    import subprocess
    import sys

    reg = _federation(tmp_path)
    reg.save()
    outs = []
    for name in ("one", "two"):
        subprocess.run([sys.executable, "-m", "lokf.cli", "registry", "build", "-r", str(reg.path),
                        "-d", str(tmp_path / name)], check=True, capture_output=True)
        outs.append((tmp_path / name / "federation.nq").read_bytes())
    assert b"_:m" in outs[0] and outs[0] == outs[1]


def test_registry_build_fails_when_nothing_loads(tmp_path):
    manifest = tmp_path / "r.yaml"
    manifest.write_text("repos:\n- base_iri: https://gone.example/\n", encoding="utf-8")
    r = runner.invoke(app, ["registry", "build", "-r", str(manifest), "-d", str(tmp_path / "out")])
    assert r.exit_code == 1 and "no member" in r.output
    bad = tmp_path / "bad.nq"
    bad.write_text("not n-quads\n", encoding="utf-8")
    q = runner.invoke(app, ["registry", "query", "--quads", str(bad), "ASK { ?s ?p ?o }"])
    assert q.exit_code == 1 and "cannot read" in q.output


def test_sensitive_members_require_explicit_clearance_before_reading(tmp_path, monkeypatch):
    from lokf.store import GraphStore
    import lokf.registry as registry_module

    reg = _federation(tmp_path)
    private = reg.repos[1]
    private.sensitivity = 'confidential'
    reads = []
    original = registry_module.member_ntriples
    def observed(entry):
        reads.append(entry.base_iri)
        return original(entry)
    monkeypatch.setattr(registry_module, 'member_ntriples', observed)
    store = GraphStore.from_registry(reg)
    assert private.base_iri not in reads
    assert 'clearance' in store.load_errors[private.base_iri]
    assert not store.ask('ASK { GRAPH <https://b.example/kb/> { ?s ?p ?o } }')
    cleared = GraphStore.from_registry(reg, cleared_members=[private.base_iri])
    assert private.base_iri in reads
    assert cleared.load_errors == {}
    assert cleared.ask('ASK { GRAPH <https://b.example/kb/> { ?s ?p ?o } }')
    assert private.sensitivity == 'confidential'


def test_cli_member_clearance_is_per_run(tmp_path):
    reg = _federation(tmp_path)
    reg.repos[1].sensitivity = 'private'
    reg.save()
    before = reg.path.read_bytes()
    query = 'ASK { GRAPH <https://b.example/kb/> { ?s ?p ?o } }'
    args = ['registry', 'query', '-r', str(reg.path), query]
    denied = runner.invoke(app, args)
    assert denied.exit_code == 0 and 'false' in denied.output and 'clearance' in denied.output
    allowed = runner.invoke(app, args + ['--clear-member', reg.repos[1].base_iri])
    assert allowed.exit_code == 0 and 'true' in allowed.output
    assert reg.path.read_bytes() == before


def test_federated_graph_preserves_cross_bundle_edges(tmp_path):
    from lokf.store import GraphStore
    from lokf.export import graph_to_cytoscape

    graph = GraphStore.from_registry(_federation(tmp_path)).rdflib_graph()
    elements = graph_to_cytoscape(graph)
    pairs = {(e['data']['source'], e['data']['target']) for e in elements['edges']}
    assert ('https://a.example/kb/x', 'https://b.example/kb/y') in pairs
