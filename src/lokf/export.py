"""Graph and search projections of a bundle, derived without rdflib.

The knowledge-graph page and JSON-LD blocks in the docs are built in a CI
environment that has neither ``rdflib`` nor the installed ``lokf`` package, so
everything here is derived from concept frontmatter and the :class:`Vocabulary`
alone. :func:`to_cytoscape` projects typed relations to edges (RDF predicates
from typed relation slots and reified ``relations`` entries, never plain
markdown body links); :func:`dataset_search_jsonld` emits schema.org
``Dataset`` documents for Google Dataset Search.
"""
from __future__ import annotations

from lokf.schema import vocabulary


def _aslist(value) -> list:
    """Coerce a scalar-or-list frontmatter value to a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def to_cytoscape(bundle, vocab=None) -> dict:
    """Bundle as cytoscape.js ``elements`` (nodes + typed-relation edges).

    Nodes are the bundle's concepts; edges are RDF predicates drawn from each
    concept's typed relation slots and reified ``relations`` entries. Local
    targets become display edges; ``external_edges`` keeps typed links to
    resources outside the bundle for concept pages without adding phantom
    nodes to the graph canvas.

    Named-slot edges match the concept-to-concept subset of
    :meth:`Bundle.graph` one-to-one and carry ``data.reified = False``. Reified
    ``relations`` entries are *flattened* to direct labeled edges for display
    (in the RDF projection they remain reified statements, not direct
    concept-to-concept triples) and are marked ``data.reified = True``.
    Non-dict ``relations`` entries are skipped; validation reports them.
    """
    from lokf import trust

    vocab = vocab or vocabulary()
    iris = bundle.by_iri()
    nodes = [
        {
            "data": {
                "id": iri,
                "label": c.title,
                "type": c.type,
                "concept_id": c.concept_id,
                # OKF v0.2 trust signals (§5), derived per node so the graph
                # explorer can show status / trust tier / staleness.
                "status": trust.effective_status(c.data),
                "trust_tier": trust.trust_tier(c.data),
                "stale": trust.is_stale(c.data),
                "edited_since_human_review": trust.edited_since_human_review(c.data),
                "refuted": bool(trust.active_refutations(c.data)),
            }
        }
        for iri, c in iris.items()
    ]
    edges: dict[tuple[str, str, str], dict] = {}
    external_edges: dict[tuple[str, str, str], dict] = {}
    for source, c in iris.items():
        # (predicate CURIE, relation name, target-ref, reified?) per concept
        assertions: list[tuple[str, str, str, bool]] = []
        for name, rel in vocab.relation_slots.items():
            if name in c.data:
                predicate = vocab.compact(rel.uri)
                for target in _aslist(c.data[name]):
                    assertions.append((predicate, name, target, False))
        for entry in _aslist(c.data.get("relations")):
            if not isinstance(entry, dict):
                continue  # malformed entry (scalar); validation reports it
            name = entry.get("predicate")
            rel = vocab.relation_types.get(name)
            target = entry.get("target")
            if rel is None or target is None:
                continue
            assertions.append((vocab.compact(rel.uri), name, target, True))
        for predicate, name, target, reified in assertions:
            # A `prefix:local` target is the IRI the schema's prefix gives it,
            # as JSON-LD reads it in the RDF projection, not a relative ref.
            tgt = bundle.resolve(vocab.expand(str(target)))
            key = (source, predicate, tgt)
            (edges if tgt in iris else external_edges).setdefault(
                key,
                {
                    "data": {
                        "id": f"{source} {predicate} {tgt}",
                        "source": source,
                        "target": tgt,
                        "predicate": predicate,
                        "slot": name,
                        "reified": reified,
                    }
                },
            )
    return {
        "nodes": nodes,
        "edges": list(edges.values()),
        "external_edges": list(external_edges.values()),
    }


def vocabulary_meta(graph: dict, vocab=None) -> dict:
    """How a site labels what *graph* holds, read from the schema: a title
    (and description) for each node ``type``; a title, and an inverse title
    where the schema gives one, for each edge ``slot``; and each type's own
    value fields. Only the types and relations the graph uses are listed."""
    vocab = vocab or vocabulary()
    types = sorted({str(n["data"]["type"]) for n in graph["nodes"] if n["data"].get("type")})
    names = sorted({
        str(e["data"]["slot"])
        for e in (*graph["edges"], *graph.get("external_edges", []))
        if e["data"].get("slot")
    })
    return {
        "types": {t: vocab.type_label(t) for t in types},
        "relations": {n: vocab.relation_label(n) for n in names},
        "fields": {t: fields for t in types if (fields := vocab.fields(t))},
    }


def graph_to_cytoscape(graph, vocab=None) -> dict:
    """Any :class:`rdflib.Graph` as cytoscape.js ``elements``.

    Nodes are resources that carry an ``rdf:type`` in the graph (labelled by
    ``schema:name``/``rdfs:label`` when present, else the local IRI part);
    edges are triples whose predicate is a LOKF relation predicate and whose
    object is itself a node. This drives the live server's visualization of a
    SPARQL ``CONSTRUCT`` result, mirroring :func:`to_cytoscape` for a store.
    """
    from rdflib import RDF, RDFS, Namespace, URIRef

    vocab = vocab or vocabulary()
    schema = Namespace("http://schema.org/")
    predicate_uris = {r.uri: vocab.compact(r.uri) for r in vocab.relation_types.values()}
    type_uris = {vocab.expand(uri): name for name, uri in vocab.classes.items()}

    def _local(iri: str) -> str:
        return iri.rstrip("/").rsplit("/", 1)[-1].rsplit("#", 1)[-1]

    def _node(iri: str) -> dict:
        rdf_type = graph.value(URIRef(iri), RDF.type)
        label = graph.value(URIRef(iri), schema.name) or graph.value(URIRef(iri), RDFS.label)
        return {
            "data": {
                "id": iri,
                "label": str(label) if label else _local(iri),
                "type": type_uris.get(str(rdf_type), _local(str(rdf_type)) if rdf_type else ""),
                "concept_id": _local(iri),
            }
        }

    # Typed resources are always nodes; resources appearing on either end of a
    # relation edge are added too, so a CONSTRUCT that omits type triples still
    # yields a connected graph.
    nodes: dict[str, dict] = {
        str(s): _node(str(s))
        for s in set(graph.subjects(RDF.type, None))
        if isinstance(s, URIRef)
    }
    edges: dict[tuple[str, str, str], dict] = {}
    for subject, predicate, obj in graph:
        p_uri = str(predicate)
        if p_uri not in predicate_uris or not isinstance(obj, URIRef):
            continue
        s, o = str(subject), str(obj)
        nodes.setdefault(s, _node(s))
        nodes.setdefault(o, _node(o))
        curie = predicate_uris[p_uri]
        key = (s, curie, o)
        edges.setdefault(
            key,
            {"data": {"id": f"{s} {curie} {o}", "source": s, "target": o,
                      "predicate": curie, "slot": curie.split(":", 1)[-1]}},
        )
    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


def dataset_search_jsonld(bundle, vocab=None) -> list[dict]:
    """schema.org ``Dataset`` JSON-LD docs for each Dataset/Table concept.

    Shaped for Google Dataset Search; only keys with values are emitted, and
    bundle-relative references (``url``/``isPartOf``/``hasPart``) are resolved
    to absolute IRIs through :meth:`Bundle.resolve`.
    """
    vocab = vocab or vocabulary()
    dataset_types = vocab.subclasses_of("Dataset")
    docs = []
    for c in bundle.concepts:
        if c.type not in dataset_types:
            continue
        iri = bundle.iri(c)
        url = c.data.get("resource")
        doc = {
            "@context": "https://schema.org/",
            "@type": "Dataset",
            "@id": iri,
            "name": c.title,
            "description": c.data.get("description"),
            "url": bundle.resolve(str(url)) if url else iri,
            "keywords": c.data.get("tags"),
            "isPartOf": [bundle.resolve(str(v)) for v in _aslist(c.data.get("isPartOf"))],
            "hasPart": [bundle.resolve(str(v)) for v in _aslist(c.data.get("hasPart"))],
        }
        docs.append({k: v for k, v in doc.items() if v})
    return docs
