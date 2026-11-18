"""Check a freshly built `lokf new` site at a domain root or project path.

Usage: python scripts/verify_scaffold_site.py SITE_DIR /[project-path]
This checks the built pages and data, rather than the template's source text.
"""

from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path


class LocalLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src", "action"} and value:
                self.values.append(value)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"scaffold site check failed: {message}")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify(site: Path, base: str) -> None:
    base = base.rstrip("/")
    prefix = base if base else ""
    url = lambda path: prefix + path
    dist = site / "dist"
    generated = site / "src" / "generated"

    required = [
        "index.html",
        "graph/index.html",
        "search/index.html",
        "glossary/active-user/index.html",
        "metrics/weekly-active-users/index.html",
        "graph.json",
        "graph.jsonld",
        "graph-index.json",
        "search-index.json",
        "graph-data/glossary/active-user/1.json",
        "graph-data/metrics/weekly-active-users/1.json",
    ]
    for name in required:
        check((dist / name).is_file(), f"missing built route {name} in {site}")
    for name in ("graph.json", "concepts.jsonld", "graph.nt"):
        check((generated / name).is_file(), f"local toolkit did not export {name}")

    graph = read_json(dist / "graph.json")
    raw = read_json(generated / "graph.json")
    concept_ids = {"glossary/active-user", "metrics/weekly-active-users"}
    nodes = {node["data"]["concept_id"]: node["data"] for node in graph["nodes"]}
    check(set(nodes) == concept_ids, "built graph has the wrong starter concepts")
    check({node["data"]["id"] for node in raw["nodes"]} ==
          {node["id"] for node in nodes.values()}, "built graph differs from toolkit export")
    for concept_id, node in nodes.items():
        check(node["href"] == url(f"/{concept_id}"), f"wrong graph link for {concept_id}")
    check(len(graph["edges"]) == len(raw["edges"]) == 1, "starter typed relation missing")
    relation = graph["edges"][0]["data"]
    check(relation["slot"] == "measures" and relation["predicate"] == "lokf:measures",
          "starter relation lost its typed predicate")
    check({relation["source"], relation["target"]} ==
          {node["id"] for node in nodes.values()}, "starter relation endpoints changed")

    jsonld = read_json(dist / "graph.jsonld")
    check({item["id"] for item in jsonld["@graph"]} ==
          {node["id"] for node in nodes.values()}, "JSON-LD does not match graph concepts")
    index = read_json(dist / "graph-index.json")
    check(index["count"] == 2 and
          {node["concept_id"] for node in index["nodes"]} == concept_ids,
          "graph navigation index is incomplete")
    for concept_id in concept_ids:
        scope = read_json(dist / f"graph-data/{concept_id}/1.json")
        check(scope["scope"]["id"] == concept_id and len(scope["nodes"]) == 2 and
              len(scope["edges"]) == 1, f"wrong bounded graph scope for {concept_id}")

    search = read_json(dist / "search-index.json")
    check({doc["concept_id"] for doc in search["documents"]} == concept_ids,
          "full-text index is missing a starter concept")
    check("active" in search["postings"] and "measures" in search["postings"],
          "full-text index is missing title or body terms")
    for doc in search["documents"]:
        check(doc["href"] == url(f"/{doc['concept_id']}"),
              f"wrong search result link for {doc['concept_id']}")

    home = (dist / "index.html").read_text(encoding="utf-8")
    graph_page = (dist / "graph/index.html").read_text(encoding="utf-8")
    search_page = (dist / "search/index.html").read_text(encoding="utf-8")
    check("Every markdown file" in home and "Browse concepts" in home,
          "home page lost the authored introduction or concept browser")
    for path in ("/search", "/graph"):
        check(f'href="{url(path)}"' in home, f"home page lacks {path} navigation")
    for attr, path in (("data-graph-src", "/graph.json"),
                       ("data-index-src", "/graph-index.json"),
                       ("data-data-base", "/graph-data/")):
        check(f'{attr}="{url(path)}"' in graph_page, f"graph explorer has wrong {attr}")
    check(f'data-index="{url("/search-index.json")}"' in search_page,
          "search page points to the wrong index")
    check("Explore a concept" in graph_page and "Find a connection path" in graph_page,
          "shared graph explorer controls did not render")

    if prefix:
        for page in dist.rglob("*.html"):
            links = LocalLinks()
            links.feed(page.read_text(encoding="utf-8"))
            for link in links.values:
                if link.startswith("/") and not link.startswith("//"):
                    check(link == prefix or link.startswith(prefix + "/") or
                          link.startswith(prefix + "?") or link.startswith(prefix + "#"),
                          f"link {link!r} in {page.relative_to(dist)} escapes {prefix}")

    payloads = {name: (dist / name).stat().st_size for name in
                ("graph.json", "graph-index.json", "search-index.json")}
    total = sum(path.stat().st_size for path in dist.rglob("*") if path.is_file())
    print(f"verified {site.name} at {base or '/'}: "
          f"{len(graph['nodes'])} concepts, {len(graph['edges'])} typed relation; "
          f"payloads {payloads}, total static bytes {total}")


def verify_domain(site: Path, base: str) -> None:
    """A CURIE target from a domain vocabulary must reach all site projections."""
    from rdflib import Graph, URIRef

    prefix = base.rstrip("/")
    dist = site / "dist"
    generated = site / "src" / "generated"
    for name in ("graph.json", "graph.jsonld", "graph-index.json",
                 "search-index.json", "graph-data/real/1.json",
                 "real/index.html", "term/index.html"):
        check((dist / name).is_file(), f"domain site is missing {name}")

    source = "https://ex.org/kb/term"
    predicate = "https://ex.org/schema/domain/taughtBy"
    target = "https://ex.org/kb/real"
    expected = {source, target}
    graph = read_json(dist / "graph.json")
    raw = read_json(generated / "graph.json")
    for title, value in (("site graph", graph), ("toolkit export", raw)):
        check({node["data"]["id"] for node in value["nodes"]} == expected,
              f"{title} lost a domain concept")
        check(len(value["edges"]) == 1, f"{title} lost the domain relation")
        edge = value["edges"][0]["data"]
        check((edge["source"], edge["predicate"], edge["target"], edge["slot"]) ==
              (source, "domain:taughtBy", target, "taughtBy"),
              f"{title} did not resolve kb:real as the taughtBy target")

    jsonld = (dist / "graph.jsonld").read_text(encoding="utf-8")
    triples = Graph().parse(data=jsonld, format="json-ld")
    check((URIRef(source), URIRef(predicate), URIRef(target)) in triples,
          "JSON-LD did not expand the domain predicate and CURIE target")
    index = read_json(dist / "graph-index.json")
    check(index["count"] == 2, "domain graph index has the wrong concept count")
    scope = read_json(dist / "graph-data/real/1.json")
    check(scope["scope"]["id"] == "real" and len(scope["edges"]) == 1,
          "domain relation is missing from the target's graph scope")

    term = (dist / "term/index.html").read_text(encoding="utf-8")
    real = (dist / "real/index.html").read_text(encoding="utf-8")
    check("Connections from this concept" in term and
          f'href="{prefix}/real"' in term and "domain:taughtBy" in term,
          "domain source page lacks its outgoing relation")
    check("Connections to this concept" in real and
          f'href="{prefix}/term"' in real and "domain:taughtBy" in real,
          "domain target page lacks its incoming backlink")
    # The schema's titles reach the pages: the type, the relation read from
    # each end (the target by the vocabulary's inverse_title), and the field
    check('class="badge"' in term and ">Module</a>" in term and ">Glossary term</a>" in real,
          "concept pages do not title their types from the schema")
    check(">Taught by</span>" in term and ">Teaches</span>" in real,
          "concept pages do not read the domain relation from both ends")
    check(">Credits</dt>" in term and "<dd>5</dd>" in term.replace("\n", ""),
          "the domain source page does not show its credits field")
    titled = graph["edges"][0]["data"]
    check((titled["title"], titled["incoming_title"]) == ("Taught by", "Teaches") and
          {node["data"]["type_title"] for node in graph["nodes"]} == {"Module", "Glossary term"},
          "the site graph does not carry the schema's titles")
    search = read_json(dist / "search-index.json")
    check({doc["concept_id"] for doc in search["documents"]} == {"real", "term"},
          "domain concepts are missing from search")
    check({doc["type_title"] for doc in search["documents"]} == {"Module", "Glossary term"},
          "domain search results do not carry type titles")
    check({doc["href"] for doc in search["documents"]} ==
          {f"{prefix}/real", f"{prefix}/term"},
          "domain search results have incorrect base links")
    print(f"verified {site.name} at {base}: domain:taughtBy resolves "
          "in graph, JSON-LD, scope, and incoming/outgoing concept pages, "
          "titled from the schema")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or not sys.argv[2].startswith("/"):
        raise SystemExit("usage: verify_scaffold_site.py SITE_DIR /[project-path] [domain]")
    if len(sys.argv) == 4 and sys.argv[3] != "domain":
        raise SystemExit("only the domain fixture mode is supported")
    if len(sys.argv) == 4:
        verify_domain(Path(sys.argv[1]), sys.argv[2])
    else:
        verify(Path(sys.argv[1]), sys.argv[2])
