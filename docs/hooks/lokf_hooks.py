"""MkDocs hooks: emit the graph JSON and inject Dataset JSON-LD.

Runs in CI where ``lokf`` is not installed and ``rdflib`` is absent, so the
repo's ``src`` directory is put on ``sys.path`` and all logic lives in
``lokf.export`` (which derives everything from frontmatter + Vocabulary).
"""
from __future__ import annotations

import json
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from lokf import load_bundle  # noqa: E402
from lokf.export import dataset_search_jsonld, to_cytoscape  # noqa: E402

_BUNDLE = _REPO / "examples" / "acme-knowledge"
_JSONLD_PAGES = ("examples.md", "graph.md")


def on_post_build(config, **kwargs):
    """Write ``site/assets/graph.json`` from the example bundle's graph."""
    out = pathlib.Path(config["site_dir"]) / "assets" / "graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    graph = to_cytoscape(load_bundle(_BUNDLE))
    out.write_text(json.dumps(graph, indent=2), encoding="utf-8")


def on_post_page(output, page, config, **kwargs):
    """Inject schema.org Dataset JSON-LD into the dataset-bearing pages."""
    if page.file.src_uri not in _JSONLD_PAGES:
        return output
    blocks = "\n".join(
        '<script type="application/ld+json">' + json.dumps(doc) + "</script>"
        for doc in dataset_search_jsonld(load_bundle(_BUNDLE))
    )
    if not blocks:
        return output
    if "</article>" in output:
        return output.replace("</article>", blocks + "\n</article>", 1)
    return output + blocks
