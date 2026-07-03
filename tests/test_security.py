"""Regression tests for the PR-3 SSRF fixes."""
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

from lokf import rdf
from lokf.server import build_server
from lokf.store import GraphStore, _uses_service

BUNDLE = "examples/acme-knowledge"


# -- SPARQL SERVICE federation is rejected ---------------------------------
def test_uses_service_detection():
    assert _uses_service("SELECT ?x { SERVICE <http://e/> { ?x ?p ?o } }")
    assert _uses_service("ASK { service <http://e/> { ?x ?p ?o } }")  # case-insensitive
    assert not _uses_service('SELECT ?x WHERE { ?x ?p "SERVICE" }')  # string literal
    assert not _uses_service("SELECT ?x WHERE { ?x ?p ?o }")


def test_service_query_rejected_at_store():
    store = GraphStore.from_bundle(BUNDLE)
    with pytest.raises(ValueError, match="SERVICE"):
        store.query("SELECT ?x WHERE { SERVICE <http://127.0.0.1:9/x> { ?x ?p ?o } }")


def test_service_query_rejected_over_http():
    store = GraphStore.from_bundle(BUNDLE)
    httpd = build_server(store, "127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        q = urllib.parse.quote("SELECT ?x { SERVICE <http://127.0.0.1:9/x> { ?x ?p ?o } }")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(f"{base}/sparql?query={q}", timeout=5)
        assert exc.value.code == 400
    finally:
        httpd.shutdown()


def test_legitimate_queries_unaffected():
    store = GraphStore.from_bundle(BUNDLE)
    assert store.select("SELECT ?s WHERE { ?s a lokf:Metric }")
    assert store.ask("ASK { ?s a lokf:Metric }") is True


# -- a concept's own @context is stripped (no remote fetch) ----------------
def test_remote_context_is_stripped(tmp_path):
    concept = tmp_path / "evil.md"
    concept.write_text(
        '---\ntype: Metric\ntitle: Evil\nid: urn:evil\n'
        '"@context": http://127.0.0.1:9/ctx.jsonld\n---\nbody\n',
        encoding="utf-8",
    )
    # Would raise a connection error if the remote @context were fetched.
    graph = rdf.graph_of(str(concept))
    assert any("urn:evil" in str(s) for s in graph.subjects())


def test_nested_context_is_stripped():
    from lokf.rdf import _strip_context

    doc = {"type": "Metric", "@context": "http://evil/", "author": {"@context": "http://evil/", "name": "x"}}
    stripped = _strip_context(doc)
    assert "@context" not in stripped
    assert "@context" not in stripped["author"]
    assert stripped["author"]["name"] == "x"
