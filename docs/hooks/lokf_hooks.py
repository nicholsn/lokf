"""MkDocs hooks: emit the graph JSON and inject Dataset JSON-LD.

Runs in CI where ``lokf`` is not installed and ``rdflib`` is absent, so the
repo's ``src`` directory is put on ``sys.path`` and all logic lives in
``lokf.export`` (which derives everything from frontmatter + Vocabulary).

The bundle and its projections are computed at most once per build: the cache
is reset in ``on_config`` and filled lazily, so ``on_post_page`` (which fires
per JSON-LD page) and ``on_post_build`` share one bundle load.
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

_cache: dict = {}


def on_config(config, **kwargs):
    """Reset the per-build cache; remember ``repo_url`` for graph metadata."""
    _cache.clear()
    _cache["repo_url"] = (config.get("repo_url") or "").rstrip("/")
    return config


def _bundle():
    if "bundle" not in _cache:
        _cache["bundle"] = load_bundle(_BUNDLE)
    return _cache["bundle"]


def _graph_json() -> str:
    """The cytoscape graph + ``meta.source_base`` as a JSON string."""
    if "graph_json" not in _cache:
        graph = to_cytoscape(_bundle())
        meta = {}
        repo_url = _cache.get("repo_url", "")
        if repo_url:
            rel = _BUNDLE.relative_to(_REPO).as_posix()
            meta["source_base"] = f"{repo_url}/tree/main/{rel}/"
        graph["meta"] = meta
        _cache["graph_json"] = json.dumps(graph, indent=2)
    return _cache["graph_json"]


def _jsonld_blocks() -> str:
    if "jsonld_blocks" not in _cache:
        _cache["jsonld_blocks"] = "\n".join(
            '<script type="application/ld+json">' + json.dumps(doc) + "</script>"
            for doc in dataset_search_jsonld(_bundle())
        )
    return _cache["jsonld_blocks"]


def on_post_page(output, page, config, **kwargs):
    """Inject schema.org Dataset JSON-LD into the dataset-bearing pages."""
    if page.file.src_uri not in _JSONLD_PAGES:
        return output
    blocks = _jsonld_blocks()
    if not blocks:
        return output
    if "</article>" in output:
        return output.replace("</article>", blocks + "\n</article>", 1)
    return output + blocks


def on_post_build(config, **kwargs):
    """Write ``site/assets/graph.json`` from the example bundle's graph."""
    out = pathlib.Path(config["site_dir"]) / "assets" / "graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_graph_json(), encoding="utf-8")
