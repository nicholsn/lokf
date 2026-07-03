"""A FastMCP stdio server that exposes the LOKF toolkit to agents.

LOKF is a semantic profile of the Open Knowledge Framework: a knowledge base
is a *bundle* of markdown *concepts* (frontmatter + prose) that projects to
RDF and is queryable with SPARQL. The tools here let an agent list and inspect
concepts, run SPARQL, convert markdown to RDF, propose typed relations from
prose links, read the relation vocabulary, and summarize a bundle. Point tools
at a bundle directory (e.g. ``examples/acme-knowledge``) unless noted.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

_INSTRUCTIONS = (
    "LOKF is a semantic profile of the Open Knowledge Framework (OKF). A "
    "knowledge base is a bundle of markdown concepts (YAML frontmatter + "
    "prose) that projects to RDF and is queryable with SPARQL. Use "
    "list_concepts/describe_concept to explore a bundle, sparql_query to ask "
    "questions of its graph (schema prefixes lokf/schema/prov/dcterms/skos/"
    "foaf/rdf/rdfs/owl/xsd/dcat are preset), convert to serialize markdown to "
    "RDF, propose_relations to mine typed relations from prose links, "
    "get_vocabulary to read the relation vocabulary, and bundle_summary for a "
    "quick orientation. Pass a bundle directory as the bundle/source argument."
)

server = FastMCP("lokf", instructions=_INSTRUCTIONS)


@server.tool()
def list_concepts(bundle: str) -> list[dict]:
    """List every concept in a bundle as {concept_id, type, title, iri}.

    ``bundle`` is a LOKF bundle directory. A fast index of what the knowledge
    base contains; use describe_concept for the full record of any one.
    """
    from lokf.model import load_bundle

    b = load_bundle(bundle)
    return [
        {
            "concept_id": c.concept_id,
            "type": c.type,
            "title": c.title,
            "iri": b.iri(c),
        }
        for c in b.concepts
    ]


@server.tool()
def describe_concept(bundle: str, concept_id: str) -> dict:
    """Describe one concept: {iri, type, title, body, frontmatter, turtle}.

    ``concept_id`` is a bundle-relative id (e.g. ``metrics/weekly-active-users``,
    with or without ``.md``). ``turtle`` is the concept's RDF projection.
    Returns {error: ...} if no concept matches.
    """
    from lokf import rdf
    from lokf.model import load_bundle

    b = load_bundle(bundle)
    wanted = concept_id.removesuffix(".md")
    concept = next((c for c in b.concepts if c.concept_id == wanted), None)
    if concept is None:
        return {"error": f"concept {concept_id!r} not found in {bundle}"}
    return {
        "iri": b.iri(concept),
        "type": concept.type,
        "title": concept.title,
        "body": concept.body,
        "frontmatter": concept.data,
        "turtle": rdf.serialize(concept.path, "ttl"),
    }


@server.tool()
def sparql_query(bundle: str, query: str) -> dict:
    """Run a SPARQL query over a bundle's in-memory graph.

    Schema prefixes (lokf/schema/prov/dcterms/skos/foaf/rdf/rdfs/owl/xsd/dcat)
    are preset, so queries need no PREFIX block. SELECT returns
    {columns: [...], rows: [{...}]}; ASK returns {boolean: bool};
    CONSTRUCT/DESCRIBE returns {turtle: '...'}. Returns {error: ...} on a bad
    query.
    """
    from lokf.store import GraphStore, query_form

    form = query_form(query)
    try:
        store = GraphStore.from_bundle(bundle)
        if form in ("construct", "describe"):
            return {"turtle": store.construct(query, fmt="ttl")}
        if form == "ask":
            return {"boolean": store.ask(query)}
        rows = store.select(query)
        columns = list(dict.fromkeys(k for row in rows for k in row))
        return {"columns": columns, "rows": rows}
    except Exception as exc:  # noqa: BLE001 — surface SPARQL errors to the agent
        return {"error": f"query failed: {exc}"}


@server.tool()
def convert(source: str, format: str = "ttl") -> dict:
    """Convert LOKF markdown to RDF: {format, rdf}.

    ``source`` is a concept .md file or a bundle directory; ``format`` is one
    of ttl | nt | jsonld | xml | n3 | trig. Returns {error: ...} for a bad
    format.
    """
    from lokf import rdf

    try:
        data = rdf.serialize(source, format)
    except ValueError as exc:
        return {"error": str(exc)}
    return {"format": format, "rdf": data}


@server.tool()
def propose_relations(
    bundle: str, min_confidence: float = 0.0, apply: bool = False
) -> list[dict]:
    """Propose typed relations from the markdown links in concept prose.

    Each proposal is {source, link_text, target, predicate, curie, confidence,
    rationale}. Proposals below ``min_confidence`` are dropped. When ``apply``
    is True the accepted proposals are written into the source files'
    frontmatter and each carries an ``applied`` flag.
    """
    from lokf.model import load_bundle
    from lokf.propose import apply as apply_proposals
    from lokf.propose import propose, proposal_row
    from lokf.schema import vocabulary

    b = load_bundle(bundle)
    proposals = [
        p
        for p in propose(b, vocabulary())
        if p.confidence >= min_confidence
    ]
    applied_ids: set[int] | None = None
    if apply:
        applied_ids = {
            id(p) for p in apply_proposals(proposals, min_confidence=min_confidence)
        }
    return [proposal_row(p, applied_ids) for p in proposals]


@server.tool()
def get_vocabulary() -> dict:
    """Return the LOKF vocabulary: {classes, relations}.

    ``classes`` maps class name -> CURIE. ``relations`` is a list of
    {name, curie, uri, frontmatter_key, description}, where ``frontmatter_key``
    is True when the relation can be asserted as a frontmatter slot (else it is
    used via a ``relations:`` entry).
    """
    from lokf.schema import vocabulary

    v = vocabulary()
    relations = sorted(v.relation_types.values(), key=lambda r: r.name)
    return {
        "classes": dict(v.classes),
        "relations": [r.as_row() for r in relations],
    }


@server.tool()
def bundle_summary(bundle: str) -> dict:
    """Summarize a bundle for quick orientation.

    Returns {concept_count, types, triple_count, relation_edge_count}: the
    number of concepts, a per-type count, the size of the RDF projection, and
    the number of typed-relation edges between concepts.
    """
    from lokf.export import to_cytoscape
    from lokf.model import load_bundle
    from lokf.store import GraphStore

    b = load_bundle(bundle)
    types: dict[str, int] = {}
    for c in b.concepts:
        types[c.type] = types.get(c.type, 0) + 1
    edges = to_cytoscape(b)["edges"]
    return {
        "concept_count": len(b.concepts),
        "types": types,
        # Reuse the already-loaded bundle instead of re-reading it from disk.
        "triple_count": len(GraphStore.from_graph(b.graph())),
        "relation_edge_count": len(edges),
    }


def main() -> None:
    """Run the LOKF MCP server over stdio."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
