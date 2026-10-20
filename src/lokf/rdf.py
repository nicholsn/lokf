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
    """Return a copy of *g* whose blank-node labels are derived from content.

    rdflib mints blank-node ids from uuid4, so identical input yields different
    labels every run. Each node is hashed from its own incoming and outgoing
    edges, iterated so nested blank nodes converge; structurally
    indistinguishable nodes then get a stable index. This only renames blank
    nodes - no triple is added, dropped or rewritten.

    (rdflib's own ``to_canonical_graph`` is not usable here: on these
    almost-entirely-blank-node SHACL graphs it returns different labels for the
    same content, the same weakness that makes ``to_isomorphic`` report a false
    negative on lokf.shacl.ttl.)
    """
    import hashlib
    from rdflib import BNode, Graph

    def hashed(term) -> dict:
        labels = {n: "0" for n in g.all_nodes() if isinstance(n, BNode)}
        for _ in range(12):
            nxt = {}
            for b in labels:
                out = sorted((str(p), labels.get(o, term(o))) for _, p, o in g.triples((b, None, None)))
                inc = sorted((labels.get(s, term(s)), str(p)) for s, p, _ in g.triples((None, None, b)))
                nxt[b] = hashlib.sha256(repr((out, inc)).encode()).hexdigest()[:24]
            if nxt == labels:
                break
            labels = nxt
        return labels

    def n3_signature(b, labels) -> tuple:
        out = sorted((str(p), labels.get(o, o.n3())) for _, p, o in g.triples((b, None, None)))
        inc = sorted((labels.get(s, s.n3()), str(p)) for s, p, _ in g.triples((None, None, b)))
        return tuple(out), tuple(inc)

    # str() cannot tell a plain "1" from a typed 1 or the IRI <1>. Nodes it
    # merges that way share a label and would take their index from rdflib's
    # random ids, so such a graph is hashed again with terms in N3 form. Only
    # then: a graph without those twins keeps the labels it always had.
    labels = hashed(str)
    groups: dict = {}
    for b, h in labels.items():
        groups.setdefault(h, []).append(b)
    if any(
        len({n3_signature(b, labels) for b in bs}) > 1 for bs in groups.values() if len(bs) > 1
    ):
        labels = hashed(lambda t: t.n3())

    buckets: dict = {}
    for b, h in sorted(labels.items(), key=lambda kv: (kv[1], str(kv[0]))):
        buckets.setdefault(h, []).append(b)
    mapping = {b: BNode(f"x{h}{i}") for h, bs in buckets.items() for i, b in enumerate(bs)}

    out_g = Graph()
    for prefix, ns in g.namespaces():
        out_g.bind(prefix, ns)
    for s, p, o in g:
        out_g.add((mapping.get(s, s), p, mapping.get(o, o)))
    return out_g


def serialize(
    source: str | pathlib.Path,
    fmt: str = "ttl",
    context: dict | None = None,
    schema: str | pathlib.Path | None = None,
) -> str:
    """Serialize a concept file or bundle to RDF text in *fmt* (default Turtle),
    under the domain *schema* when one is given.

    Nested objects (sources, verified events, distributions) project as blank
    nodes, which rdflib labels at random. They are relabelled from content and
    N-Triples lines sorted, so the same bundle always gives the same bytes.
    """
    rdflib_fmt = _rdflib_format(fmt)
    g = relabel_bnodes(graph_of(source, context, schema=schema))
    data = g.serialize(format=rdflib_fmt)
    text = data if isinstance(data, str) else data.decode("utf-8")
    if rdflib_fmt == "nt":
        text = "\n".join(sorted(line for line in text.splitlines() if line.strip())) + "\n"
    return text
