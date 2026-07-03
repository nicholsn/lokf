"""Regression tests for the PR-3 review fixes."""
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

from lokf.cli import main
from lokf.server import build_server
from lokf.store import GraphStore, query_form

BUNDLE = "examples/acme-knowledge"


# -- query_form: comments and PREFIX/BASE are skipped ----------------------
@pytest.mark.parametrize(
    "sparql,expected",
    [
        ("# a note\nCONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", "construct"),
        ("# c\nASK { ?s ?p ?o }", "ask"),
        ("PREFIX x: <urn:x>\n# c\nSELECT ?s WHERE { ?s ?p ?o }", "select"),
        ("DESCRIBE <urn:x>", "describe"),
        ("  \n  SELECT ?s {}", "select"),
    ],
)
def test_query_form_skips_comments_and_prefixes(sparql, expected):
    assert query_form(sparql) == expected


def test_comment_led_construct_query_routes_correctly():
    # A comment-led CONSTRUCT must run as a CONSTRUCT, not fall through to SELECT.
    ttl = GraphStore.from_bundle(BUNDLE).construct(
        "# derivations\nCONSTRUCT { ?s prov:wasDerivedFrom ?o } "
        "WHERE { ?s prov:wasDerivedFrom ?o }"
    )
    assert "prov:wasDerivedFrom" in ttl


# -- select keeps unbound variables as columns -----------------------------
def test_select_column_complete_for_all_unbound_variable():
    rows = GraphStore.from_bundle(BUNDLE).select(
        "SELECT ?name ?missing WHERE { ?m schema:name ?name "
        "OPTIONAL { ?m lokf:noSuchSlot ?missing } }"
    )
    assert all("missing" in row for row in rows)


# -- CLI main() surfaces exit codes ----------------------------------------
def test_main_returns_nonzero_for_bad_format(tmp_path):
    assert main(["convert", f"{BUNDLE}/glossary/active-user.md", "-f", "nope"]) == 2


def test_main_returns_nonzero_for_unknown_skills_action():
    assert main(["skills", "bogus-action"]) == 2


def test_main_returns_nonzero_for_frontmatterless_file():
    # log.md is a reserved bundle file with no YAML frontmatter.
    assert main(["convert", f"{BUNDLE}/log.md", "-f", "ttl"]) == 2


def test_main_returns_nonzero_for_missing_path():
    # A nonexistent path is a UsageError (exists=True), surfaced as exit 2.
    assert main(["convert", "/no/such/file.md"]) == 2


# -- server hardening ------------------------------------------------------
def _serve():
    httpd = build_server(GraphStore.from_bundle(BUNDLE), "127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def test_graph_json_rejects_non_construct_query():
    httpd, base = _serve()
    try:
        q = urllib.parse.quote("SELECT ?s WHERE { ?s ?p ?o }")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(f"{base}/graph.json?query={q}", timeout=5)
        assert exc.value.code == 400
        assert b"CONSTRUCT" in exc.value.read()
    finally:
        httpd.shutdown()


def test_post_bad_content_length_is_clean_400():
    # A malformed Content-Length must yield a controlled 400, not a 500/crash.
    # urllib recomputes the header, so drive a raw socket.
    import socket

    httpd, base = _serve()
    host, port = httpd.server_address[0], httpd.server_address[1]
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.sendall(
            b"POST /sparql HTTP/1.1\r\nHost: x\r\n"
            b"Content-Type: application/x-www-form-urlencoded\r\n"
            b"Content-Length: not-a-number\r\n\r\n"
        )
        status = sock.recv(64).split(b" ")[1]
        sock.close()
        assert status == b"400"
    finally:
        httpd.shutdown()


def test_post_valid_query_still_works():
    httpd, base = _serve()
    try:
        import json

        req = urllib.request.Request(
            f"{base}/sparql", data=b"query=" + urllib.parse.quote("ASK { ?s ?p ?o }").encode()
        )
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        assert json.loads(urllib.request.urlopen(req, timeout=5).read())["boolean"] is True
    finally:
        httpd.shutdown()
