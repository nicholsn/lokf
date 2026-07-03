"""Graph and search projections of a bundle, derived without rdflib.

The knowledge-graph page and JSON-LD blocks in the docs are built in a CI
environment that has neither ``rdflib`` nor the installed ``lokf`` package, so
everything here is derived from concept frontmatter and the :class:`Vocabulary`
alone. :func:`to_cytoscape` reproduces the concept-to-concept subset of the RDF
projection (its edges are RDF predicates from typed relation slots, never plain
markdown body links); :func:`dataset_search_jsonld` emits schema.org
``Dataset`` documents for Google Dataset Search.
"""
from __future__ import annotations

from lokf.schema import load_schema, vocabulary


def _descends_from(classes: dict, name: str, ancestor: str) -> bool:
    """Whether class ``name`` is ``ancestor`` or one of its subclasses."""
    while name is not None:
        if name == ancestor:
            return True
        name = classes.get(name, {}).get("is_a")
    return False


def _dataset_types(schema: dict) -> set[str]:
    """The set of type names that are ``Dataset`` or a subclass (e.g. Table)."""
    classes = schema.get("classes", {})
    return {n for n in classes if _descends_from(classes, n, "Dataset")}


def _aslist(value) -> list:
    """Coerce a scalar-or-list frontmatter value to a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def to_cytoscape(bundle, vocab=None) -> dict:
    """Bundle as cytoscape.js ``elements`` (nodes + typed-relation edges).

    Nodes are the bundle's concepts; edges are RDF predicates drawn from each
    concept's typed relation slots and reified ``relations`` entries, keeping
    only those whose target resolves to another concept in the bundle. The edge
    set equals the concept-to-concept subset of :meth:`Bundle.graph`.
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
        # (predicate CURIE, relation name, target-ref) triples for this concept
        assertions: list[tuple[str, str, str]] = []
        for name, rel in vocab.relation_slots.items():
            if name in c.data:
                predicate = vocab.compact(rel.uri)
                for target in _aslist(c.data[name]):
                    assertions.append((predicate, name, target))
        for entry in _aslist(c.data.get("relations")):
            name = entry.get("predicate")
            rel = vocab.relation_types.get(name)
            target = entry.get("target")
            if rel is None or target is None:
                continue
            assertions.append((vocab.compact(rel.uri), name, target))
        for predicate, name, target in assertions:
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
                    }
                },
            )
    return {"nodes": nodes, "edges": list(edges.values())}


def dataset_search_jsonld(bundle, vocab=None) -> list[dict]:
    """schema.org ``Dataset`` JSON-LD docs for each Dataset/Table concept.

    Shaped for Google Dataset Search; only keys with values are emitted.
    """
    dataset_types = _dataset_types(load_schema())
    docs = []
    for c in bundle.concepts:
        if c.type not in dataset_types:
            continue
        iri = bundle.iri(c)
        doc = {
            "@context": "https://schema.org/",
            "@type": "Dataset",
            "@id": iri,
            "name": c.title,
            "description": c.data.get("description"),
            "url": c.data.get("resource") or iri,
            "keywords": c.data.get("tags"),
            "isPartOf": c.data.get("isPartOf"),
            "hasPart": c.data.get("hasPart"),
        }
        docs.append({k: v for k, v in doc.items() if v})
    return docs
