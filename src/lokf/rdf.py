"""Convert LOKF markdown (a single concept or a whole bundle) to RDF.

This is the engine behind ``lokf convert``. A concept file is lifted to
JSON-LD via the published context and parsed with rdflib, so it serializes to
any format rdflib supports.

    from lokf import rdf

    print(rdf.serialize("examples/acme-knowledge/metrics/weekly-active-users.md"))
    print(rdf.serialize("examples/acme-knowledge", fmt="nt"))
"""
from __future__ import annotations

import json
import pathlib

from lokf.parse import parse_concept
from lokf.schema import load_context

# CLI/RDF short names -> the format rdflib understands.
FORMATS: dict[str, str] = {
    "ttl": "turtle",
    "turtle": "turtle",
    "nt": "nt",
    "ntriples": "nt",
    "n-triples": "nt",
    "jsonld": "json-ld",
    "json-ld": "json-ld",
    "xml": "xml",
    "rdfxml": "xml",
    "rdf": "xml",
    "n3": "n3",
    "trig": "trig",
}


def _rdflib_format(fmt: str) -> str:
    key = fmt.lower()
    if key not in FORMATS:
        raise ValueError(
            f"unknown format {fmt!r}; choose from {', '.join(sorted(FORMATS))}"
        )
    return FORMATS[key]


def docs_to_graph(docs: list[dict], context: dict | None = None):
    """Parse a list of concept docs into one :class:`rdflib.Graph`.

    The docs are wrapped in a single ``@graph`` JSON-LD document so the
    context is compiled once. This is the shared seam behind
    :meth:`lokf.model.Bundle.graph` and :func:`graph_of`.
    """
    from rdflib import Graph

    ctx = context if context is not None else load_context()
    g = Graph()
    g.parse(
        data=json.dumps({"@context": ctx, "@graph": docs}),
        format="json-ld",
    )
    return g


def _bundle_root(path: pathlib.Path) -> pathlib.Path | None:
    """The nearest ancestor directory that is a bundle root (has ``index.md``)."""
    for parent in path.parents:
        if (parent / "index.md").exists():
            return parent
    return None


def graph_of(source: str | pathlib.Path, context: dict | None = None):
    """RDF graph for a concept file or a bundle directory.

    A directory is projected as a whole bundle. A single ``.md`` file is
    resolved against its enclosing bundle when one exists (so ``id`` follows
    the bundle's ``base_iri``); a standalone file falls back to its explicit
    ``id`` or a ``file://`` IRI derived from its path.
    """
    from lokf.model import load_bundle

    path = pathlib.Path(source)
    if path.is_dir():
        return load_bundle(path).graph(context)

    root = _bundle_root(path)
    if root is not None:
        bundle = load_bundle(root)
        concept = next(
            (c for c in bundle.concepts if c.path.resolve() == path.resolve()),
            None,
        )
        if concept is not None:
            doc = dict(concept.data)
            doc.setdefault("id", bundle.iri(concept))
            return docs_to_graph([doc], context)

    # Standalone concept file: honor an explicit id, else mint a file:// IRI.
    doc = parse_concept(str(path))
    doc.setdefault("id", path.resolve().as_uri())
    return docs_to_graph([doc], context)


def serialize(
    source: str | pathlib.Path, fmt: str = "ttl", context: dict | None = None
) -> str:
    """Serialize a concept file or bundle to RDF text in *fmt* (default Turtle)."""
    g = graph_of(source, context)
    data = g.serialize(format=_rdflib_format(fmt))
    return data if isinstance(data, str) else data.decode("utf-8")
