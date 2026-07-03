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
    concept's typed relation slots and reified ``relations`` entries, keeping
    only those whose target resolves to another concept in the bundle.

    Named-slot edges match the concept-to-concept subset of
    :meth:`Bundle.graph` one-to-one and carry ``data.reified = False``. Reified
    ``relations`` entries are *flattened* to direct labeled edges for display
    (in the RDF projection they remain reified statements, not direct
    concept-to-concept triples) and are marked ``data.reified = True``.
    Non-dict ``relations`` entries are skipped; validation reports them.
    """
    vocab = vocab or vocabulary()
    iris = {bundle.iri(c): c for c in bundle.concepts}
    nodes = [
        {
            "data": {
                "id": iri,
                "label": c.title,
                "type": c.type,
                "concept_id": c.concept_id,
            }
        }
        for iri, c in iris.items()
    ]
    edges: dict[tuple[str, str, str], dict] = {}
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
            tgt = bundle.resolve(str(target))
            if tgt not in iris:
                continue
            key = (source, predicate, tgt)
            edges.setdefault(
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
    return {"nodes": nodes, "edges": list(edges.values())}


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
