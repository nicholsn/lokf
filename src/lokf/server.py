"""A local SPARQL endpoint + live graph visualization for a knowledge base.

``lokf serve <bundle>`` loads the bundle into a :class:`~lokf.store.GraphStore`
and publishes it over HTTP so agents (and people) can query and explore it
locally — no external services, entirely offline:

* ``GET|POST /sparql`` — the SPARQL 1.1 protocol. SELECT/ASK return
  ``application/sparql-results+json``; CONSTRUCT/DESCRIBE return Turtle.
* ``GET /graph.json`` — cytoscape.js elements for the whole graph.
* ``GET /`` — an interactive cytoscape view with a live SPARQL box.

The server is stdlib-only (``http.server``); cytoscape.js ships in the package.
"""
from __future__ import annotations

import json
import pathlib
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from lokf.store import GraphStore

_STATIC = pathlib.Path(__file__).resolve().parent / "static"
_QUERY_FORM = re.compile(
    r"^\s*(?:(?:prefix|base)\b[^\n]*\n\s*)*\s*(select|ask|construct|describe)\b",
    re.IGNORECASE,
)


def _query_form(sparql: str) -> str:
    m = _QUERY_FORM.match(sparql)
    return m.group(1).lower() if m else "select"


def _handler_class(store: GraphStore):
    """Build a request handler bound to *store* (one store per server)."""

    class LokfHandler(BaseHTTPRequestHandler):
        server_version = "lokf-server"

        def log_message(self, *args):  # keep the console quiet
            pass

        # -- helpers --------------------------------------------------------
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _sparql(self, sparql: str) -> None:
            if not sparql:
                self._send(400, b"missing query", "text/plain")
                return
            try:
                if _query_form(sparql) in ("construct", "describe"):
                    body = store.construct(sparql, fmt="ttl").encode("utf-8")
                    self._send(200, body, "text/turtle")
                else:
                    body = store.serialize_results(sparql, "json")
                    self._send(200, body, "application/sparql-results+json")
            except Exception as exc:  # noqa: BLE001 — report SPARQL errors as 400
                self._send(400, str(exc).encode("utf-8"), "text/plain")

        # -- routes ---------------------------------------------------------
        def do_GET(self):
            route = urlparse(self.path)
            if route.path == "/":
                self._send(200, _INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif route.path == "/graph.json":
                from lokf.export import graph_to_cytoscape

                params = parse_qs(route.query)
                sparql = (params.get("query") or [None])[0]
                try:
                    graph = store.rdflib_graph(sparql)
                except Exception as exc:  # noqa: BLE001 — bad CONSTRUCT → 400
                    self._send(400, str(exc).encode("utf-8"), "text/plain")
                    return
                elements = graph_to_cytoscape(graph)
                self._send(200, json.dumps(elements).encode("utf-8"), "application/json")
            elif route.path == "/static/cytoscape.min.js":
                data = (_STATIC / "cytoscape.min.js").read_bytes()
                self._send(200, data, "application/javascript")
            elif route.path == "/sparql":
                params = parse_qs(route.query)
                self._sparql((params.get("query") or [""])[0])
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if urlparse(self.path).path != "/sparql":
                self._send(404, b"not found", "text/plain")
                return
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            ctype = self.headers.get("Content-Type", "")
            if ctype.startswith("application/x-www-form-urlencoded"):
                sparql = (parse_qs(raw).get("query") or [""])[0]
            else:  # application/sparql-query
                sparql = raw
            self._sparql(sparql)

    return LokfHandler


def build_server(store: GraphStore, host: str = "127.0.0.1", port: int = 8000):
    """A :class:`ThreadingHTTPServer` serving *store* (start/stop it yourself)."""
    return ThreadingHTTPServer((host, port), _handler_class(store))


def serve(source, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Load *source* and serve it until interrupted."""
    store = GraphStore.from_bundle(source)
    httpd = build_server(store, host, port)
    bound_host, bound_port = httpd.server_address[0], httpd.server_address[1]
    print(f"lokf: {len(store)} triples from {source}")
    print(f"lokf: SPARQL endpoint  http://{bound_host}:{bound_port}/sparql")
    print(f"lokf: graph explorer   http://{bound_host}:{bound_port}/")
    print("lokf: Ctrl-C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()


_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>LOKF graph explorer</title>
<style>
  :root { color-scheme: light dark; }
  body { margin: 0; font: 14px/1.5 system-ui, sans-serif; }
  header { padding: .6rem 1rem; border-bottom: 1px solid #8883; }
  header strong { font-size: 1.05rem; }
  header span { color: #8888; margin-left: .5rem; }
  .bar { display: flex; gap: .5rem; padding: .6rem 1rem; }
  .bar textarea { flex: 1; font-family: ui-monospace, monospace; font-size: 13px;
    padding: .4rem; min-height: 3.2rem; resize: vertical; }
  .bar button { padding: 0 1rem; cursor: pointer; }
  #cy { height: 65vh; border-top: 1px solid #8883; }
  #status { padding: .3rem 1rem; color: #8888; font-size: 12px; min-height: 1rem; }
</style>
</head>
<body>
<header><strong>LOKF graph explorer</strong>
  <span>edges are RDF predicates; run a CONSTRUCT to reshape the view</span></header>
<div class="bar">
  <textarea id="q">CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }</textarea>
  <button id="run">Run &amp; draw</button>
</div>
<div id="status"></div>
<div id="cy"></div>
<script src="/static/cytoscape.min.js"></script>
<script>
const PALETTE = ["#5b8def","#e8833a","#2ea77d","#c1558b","#9b6dd6","#d2b13a","#4bacc6","#d05b5b"];
const status = document.getElementById("status");
let cy;

function draw(elements) {
  const types = [...new Set(elements.nodes.map(n => n.data.type))];
  const colorOf = {};
  types.forEach((t, i) => colorOf[t] = PALETTE[i % PALETTE.length]);
  elements.nodes.forEach(n => n.data.color = colorOf[n.data.type]);
  if (cy) cy.destroy();
  cy = cytoscape({
    container: document.getElementById("cy"),
    elements,
    layout: { name: "cose", padding: 30, idealEdgeLength: 130, nodeRepulsion: 9000 },
    style: [
      { selector: "node", style: { "background-color": "data(color)", "label": "data(label)",
        "font-size": "11px", "text-wrap": "wrap", "text-max-width": "120px",
        "text-valign": "bottom", "text-margin-y": 4, "width": 26, "height": 26 } },
      { selector: "edge", style: { "label": "data(predicate)", "font-size": "9px",
        "curve-style": "bezier", "target-arrow-shape": "triangle", "width": 1.5,
        "line-color": "#888", "target-arrow-color": "#888", "color": "#888",
        "text-rotation": "autorotate" } }
    ]
  });
  status.textContent = elements.nodes.length + " nodes, " + elements.edges.length + " edges";
}

async function loadDefault() {
  const r = await fetch("/graph.json");
  draw(await r.json());
}

document.getElementById("run").addEventListener("click", async () => {
  const query = document.getElementById("q").value;
  status.textContent = "running…";
  // /graph.json runs the CONSTRUCT server-side and returns cytoscape elements,
  // so the drawn graph is exactly the CONSTRUCT result.
  const r = await fetch("/graph.json?query=" + encodeURIComponent(query));
  if (!r.ok) { status.textContent = "error: " + (await r.text()); return; }
  draw(await r.json());
});

loadDefault().catch(e => status.textContent = "load failed: " + e);
</script>
</body>
</html>
"""
