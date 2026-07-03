"""Tests for ``lokf.server`` — the local SPARQL endpoint + graph viz.

Each test spins a :class:`ThreadingHTTPServer` on an ephemeral port in a daemon
thread and always shuts it down in a ``finally`` block.
"""
from __future__ import annotations

import json
import pathlib
import threading
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager

from lokf.server import build_server
from lokf.store import GraphStore

BUNDLE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "acme-knowledge"

_SELECT = "SELECT ?name WHERE { ?m a lokf:Metric ; schema:name ?name }"
_CONSTRUCT = (
    "CONSTRUCT { ?s prov:wasDerivedFrom ?o } WHERE { ?s prov:wasDerivedFrom ?o }"
)


@contextmanager
def _running_server():
    """Yield the base URL of a live server, shutting it down afterward."""
    store = GraphStore.from_bundle(BUNDLE)
    httpd = build_server(store, "127.0.0.1", 0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def _get(base, path):
    with urllib.request.urlopen(base + path) as resp:
        return resp.status, resp.headers.get("Content-Type", ""), resp.read()


def test_sparql_select_returns_results_json():
    """GET /sparql?query=<SELECT> -> 200 sparql-results+json with the WAU row."""
    with _running_server() as base:
        status, ctype, body = _get(
            base, "/sparql?query=" + urllib.parse.quote(_SELECT)
        )
    assert status == 200
    assert ctype == "application/sparql-results+json"
    doc = json.loads(body)
    assert doc["results"]["bindings"][0]["name"]["value"] == "Weekly Active Users"


def test_sparql_construct_returns_turtle():
    """GET /sparql?query=<CONSTRUCT> -> 200 text/turtle."""
    with _running_server() as base:
        status, ctype, body = _get(
            base, "/sparql?query=" + urllib.parse.quote(_CONSTRUCT)
        )
    assert status == 200
    assert ctype == "text/turtle"
    assert b"wasDerivedFrom" in body or b"prov:" in body


def test_sparql_post_urlencoded_ask_returns_boolean_json():
    """POST /sparql (urlencoded query=) ASK -> 200 boolean results JSON."""
    data = urllib.parse.urlencode({"query": "ASK { ?m a lokf:Metric }"}).encode()
    with _running_server() as base:
        req = urllib.request.Request(
            base + "/sparql",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = resp.read()
    assert status == 200
    assert json.loads(body)["boolean"] is True


def test_graph_json_full_graph():
    """GET /graph.json -> cytoscape elements with >=6 nodes and >=8 edges."""
    with _running_server() as base:
        _, ctype, body = _get(base, "/graph.json")
    assert ctype == "application/json"
    els = json.loads(body)
    assert len(els["nodes"]) >= 6
    assert len(els["edges"]) >= 8


def test_graph_json_construct_yields_smaller_connected_graph():
    """A CONSTRUCT scoped to derivedFrom draws a small connected subgraph."""
    with _running_server() as base:
        _, _, body = _get(
            base, "/graph.json?query=" + urllib.parse.quote(_CONSTRUCT)
        )
    els = json.loads(body)
    assert len(els["nodes"]) >= 2
    assert len(els["edges"]) >= 1
    assert len(els["nodes"]) < 6  # smaller than the full graph


def test_index_html_references_static_cytoscape():
    """GET / -> 200 HTML referencing /static/cytoscape.min.js."""
    with _running_server() as base:
        status, ctype, body = _get(base, "/")
    assert status == 200
    assert ctype.startswith("text/html")
    assert b"/static/cytoscape.min.js" in body


def test_static_cytoscape_served_non_empty():
    """GET /static/cytoscape.min.js -> 200 non-empty body."""
    with _running_server() as base:
        status, _, body = _get(base, "/static/cytoscape.min.js")
    assert status == 200
    assert len(body) > 0


def test_unknown_path_404():
    """An unmatched route returns 404."""
    with _running_server() as base:
        try:
            _get(base, "/nonexistent")
            raise AssertionError("expected HTTPError")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404


def test_malformed_sparql_400():
    """A malformed SPARQL query returns 400."""
    with _running_server() as base:
        try:
            _get(base, "/sparql?query=" + urllib.parse.quote("SELEC broken"))
            raise AssertionError("expected HTTPError")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
