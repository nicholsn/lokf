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
from lokf.schema import schema_context

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


def _strip_context(obj):
    """Recursively drop any ``@context`` keys from concept data.

    Concepts get their meaning from the trusted published context attached to
    the wrapper; a concept that declares its own ``@context`` (e.g. a remote
    IRI in attacker-supplied frontmatter) would otherwise make the JSON-LD
    parser fetch that URL — an SSRF vector. Stripping it closes that.
    """
    if isinstance(obj, dict):
        return {k: _strip_context(v) for k, v in obj.items() if k != "@context"}
    if isinstance(obj, list):
        return [_strip_context(v) for v in obj]
    return obj


def _as_declared_type(doc: dict, classes: set[str]) -> dict:
    """Type an unknown ``type`` as ``Concept``, keeping the producer's string.

    ``type`` is the JSON-LD ``@type`` alias, so an OKF type the schema does
    not declare would either mint an undeclared ``lokf:<Type>`` class or, for
    a spaced spelling such as ``BigQuery Table``, expand to an invalid IRI the
    parser drops — leaving the node untyped. SPEC §8 says unknown types are
    read as ``lokf:Concept``; the original spelling goes to
    ``additionalType`` (``schema:additionalType``) so it is not lost.
    """
    t = doc.get("type")
    if not isinstance(t, str) or t in classes:
        return doc
    out = dict(doc)
    out["type"] = "Concept"
    out.setdefault("additionalType", t)
    return out


def docs_to_graph(
    docs: list[dict],
    context: dict | None = None,
    base: str | None = None,
    schema: str | pathlib.Path | None = None,
):
    """Parse a list of concept docs into one :class:`rdflib.Graph`.

    The docs are wrapped in a single ``@graph`` JSON-LD document so the
    context is compiled once. This is the shared seam behind
    :meth:`lokf.model.Bundle.graph` and :func:`graph_of`.

    ``base`` (normally the bundle's ``base_iri``) anchors relative ``@id``
    values — concept ids are injected absolute, but OKF v0.2 ``sources[].id``
    keys are relative and would otherwise resolve against the local file
    system.

    ``schema`` is a domain schema to project under. Its context replaces the
    published one unless *context* is given, and its classes count as
    declared, so a domain type keeps its own class instead of reading as
    ``lokf:Concept``.
    """
    from rdflib import BNode, Graph, URIRef
    from rdflib.namespace import RDF

    from lokf.schema import vocabulary

    ctx = context if context is not None else schema_context(schema)
    classes = set(vocabulary(schema).classes)
    docs = [_as_declared_type(_strip_context(d), classes) for d in docs]
    g = Graph()
    g.parse(
        data=json.dumps({"@context": ctx, "@graph": docs}),
        format="json-ld",
        publicID=base or None,
    )
    # JSON-LD's @id coercion connects an inlined audience but does not
    # infer its class from the LinkML range. Supply the declared default
    # so projected audiences satisfy the generated SHACL class constraint.
    # Work with expanded IRIs so a custom context's unrelated `audience`
    # property is unaffected, and preserve explicitly typed audiences.
    for audience in list(g.objects(None, URIRef("http://schema.org/audience"))):
        if isinstance(audience, (BNode, URIRef)) and not any(g.objects(audience, RDF.type)):
            g.add((audience, RDF.type, URIRef("http://schema.org/PeopleAudience")))
    return g


def _bundle_root(path: pathlib.Path) -> pathlib.Path | None:
    """The nearest ancestor directory that is a bundle root (has ``index.md``)."""
    for parent in path.parents:
        if (parent / "index.md").exists():
            return parent
    return None


def graph_of(
    source: str | pathlib.Path,
    context: dict | None = None,
    schema: str | pathlib.Path | None = None,
):
    """RDF graph for a concept file or a bundle directory.

    A directory is projected as a whole bundle. A single ``.md`` file is
    resolved against its enclosing bundle when one exists (so ``id`` follows
    the bundle's ``base_iri``); a standalone file falls back to its explicit
    ``id`` or a ``file://`` IRI derived from its path. ``schema`` is as for
    :func:`docs_to_graph`.
    """
    from lokf.model import load_bundle

    path = pathlib.Path(source)
    if path.is_dir():
        return load_bundle(path).graph(context, schema=schema)

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
            return docs_to_graph([doc], context, base=bundle.base_iri or None, schema=schema)

    # Standalone concept file: honor an explicit id, else mint a file:// IRI.
    doc = parse_concept(str(path))
    doc.setdefault("id", path.resolve().as_uri())
    return docs_to_graph([doc], context, schema=schema)


def relabel_bnodes(g):
    """Copy a graph with canonical blank-node labels, preserving its triples.

    Refinement alone cannot distinguish all nodes (long paths and symmetric
    cycles are common counterexamples). RDFLib's canonicalizer resolves such
    ties structurally instead of breaking them with random source node IDs.
    """
    from rdflib import Graph
    from rdflib.compare import to_canonical_graph
    from rdflib.graph import DATASET_DEFAULT_GRAPH_ID

    out = Graph(identifier=DATASET_DEFAULT_GRAPH_ID)
    for prefix, ns in g.namespaces():
        out.bind(prefix, ns)
    for triple in to_canonical_graph(g):
        out.add(triple)
    return out


def _sorted_jsonld(text: str) -> str:
    """rdflib's JSON-LD with its node list and value arrays in a fixed order.

    Both are unordered in JSON-LD, and rdflib fills them in whatever order its
    store hands back, so the same graph prints differently from run to run.
    An ``@list`` keeps its order: it is the one ordered array.
    """
    def key(value) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)

    def node(obj):
        if not isinstance(obj, dict):
            return obj
        return {k: (sorted((node(v) for v in vs), key=key)
                    if isinstance(vs, list) and k != "@list" else vs)
                for k, vs in obj.items()}

    data = json.loads(text)
    if isinstance(data, list):
        data = sorted((node(n) for n in data), key=lambda n: (n.get("@id", ""), key(n)))
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def serialize_graph(g, fmt: str = "ttl", prefixes: dict[str, str] | None = None) -> str:
    """Serialize *g* to RDF text in *fmt*, the same bytes for the same graph.

    Blank nodes, which rdflib labels at random, are relabelled from content,
    N-Triples lines sorted and JSON-LD arrays put in order, so N-Triples,
    Turtle, N3, TriG and JSON-LD come out the same every run. RDF/XML keeps
    the same labels, but rdflib may order its descriptions differently.
    *prefixes* are bound over rdflib's defaults, which map ``schema:`` to
    https://schema.org/ and would leave LOKF's http://schema.org/ terms as
    ``schema1:``.
    """
    rdflib_fmt = _rdflib_format(fmt)
    g = relabel_bnodes(g)
    for prefix, ns in (prefixes or {}).items():
        g.bind(prefix, ns, override=True, replace=True)
    data = g.serialize(format=rdflib_fmt)
    text = data if isinstance(data, str) else data.decode("utf-8")
    if rdflib_fmt == "json-ld":
        text = _sorted_jsonld(text)
    if rdflib_fmt == "nt":
        # Split on newlines only: N-Triples escapes them, but writes other
        # line breaks a literal may hold (U+2028, U+0085, form feed) as they are.
        text = "\n".join(sorted(line for line in text.split("\n") if line.strip())) + "\n"
    return text


def serialize(
    source: str | pathlib.Path,
    fmt: str = "ttl",
    context: dict | None = None,
    schema: str | pathlib.Path | None = None,
) -> str:
    """Serialize a concept file or bundle to RDF text in *fmt* (default Turtle),
    under the domain *schema* when one is given, the same bytes for the same
    bundle (see :func:`serialize_graph`)."""
    from lokf.schema import vocabulary

    return serialize_graph(
        graph_of(source, context, schema=schema), fmt, vocabulary(schema).prefixes
    )
