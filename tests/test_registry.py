"""Tests for the cross-bundle registry (meta-lokf) — SPEC §11.

Covers the offline Phase 1 engine: longest-``base_iri``-prefix routing, the
explicit-``id`` fallback, the registration guards, entry building from a local
bundle, and the ``lokf registry`` CLI round-trip.
"""
from __future__ import annotations

import pathlib

import pytest
import yaml
from typer.testing import CliRunner

from lokf.cli import app
from lokf.registry import (
    VOCAB_NS,
    RepoEntry,
    Registry,
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
    assert entry.void["triples"] == 86
    # Six concepts, each a distinct type; all route by prefix, so id_index empty.
    assert sum(entry.void["class_partition"].values()) == 6
    assert entry.id_index == {}


def _write_bundle(root: pathlib.Path, base_iri: str, concept: str, explicit_id: str | None):
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.md").write_text(f"---\nbase_iri: {base_iri}\ntitle: T\n---\n", encoding="utf-8")
    fm = f"id: {explicit_id}\n" if explicit_id else ""
    (root / f"{concept}.md").write_text(
        f"---\n{fm}type: Concept\ntitle: Thing\n---\nbody\n", encoding="utf-8"
    )


def test_entry_for_bundle_harvests_diverging_explicit_id(tmp_path):
    """A concept whose explicit id escapes base_iri lands in id_index."""
    root = tmp_path / "kb"
    _write_bundle(root, "https://ex.org/kb/", "legacy", "https://ex.org/legacy/thing")
    entry = entry_for_bundle(root)
    assert entry.id_index == {"https://ex.org/legacy/thing": "legacy"}


# -- CLI round-trip ---------------------------------------------------------
def test_cli_init_add_list_resolve(tmp_path):
    manifest = tmp_path / "lokf-registry.yaml"
    assert runner.invoke(app, ["registry", "init", "-r", str(manifest)]).exit_code == 0
    assert manifest.exists()

    add = runner.invoke(
        app,
        ["registry", "add", str(BUNDLE), "-r", str(manifest), "--source-base", "https://x/"],
    )
    assert add.exit_code == 0 and "86 triples" in add.output

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


def test_cli_list_missing_manifest_is_clean_error(tmp_path):
    r = runner.invoke(app, ["registry", "list", "-r", str(tmp_path / "nope.yaml")])
    assert r.exit_code == 1 and "not found" in r.output


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
