"""A pyoxigraph-backed RDF store for querying a LOKF knowledge base.

Load a bundle (or any RDF graph) into an in-memory Oxigraph store and run
SPARQL over it — the knowledge-retrieval layer of the toolkit.

    from lokf.store import GraphStore

    store = GraphStore.from_bundle("examples/acme-knowledge")
    for row in store.select("SELECT ?s WHERE { ?s a lokf:Metric }"):
        print(row["s"])
"""
from __future__ import annotations

import pathlib

import pyoxigraph as ox

from lokf.schema import vocabulary

# SPARQL results short names -> pyoxigraph result format.
_RESULT_FORMATS = {
    "json": ox.QueryResultsFormat.JSON,
    "xml": ox.QueryResultsFormat.XML,
    "csv": ox.QueryResultsFormat.CSV,
    "tsv": ox.QueryResultsFormat.TSV,
}


def _prefix_header(prefixes: dict[str, str]) -> str:
    return "".join(f"PREFIX {p}: <{ns}>\n" for p, ns in prefixes.items())


class GraphStore:
    """An in-memory SPARQL store over a LOKF knowledge base.

    ``prefixes`` (the schema's namespace table) are prepended to every query
    and update, so ``lokf:``/``schema:``/``prov:`` and friends work without a
    per-query ``PREFIX`` block.
    """

    def __init__(self, store: ox.Store, prefixes: dict[str, str] | None = None):
        self.store = store
        self.prefixes = prefixes if prefixes is not None else vocabulary().prefixes

    # -- construction -------------------------------------------------------
    @classmethod
    def from_rdf(cls, data: str | bytes, fmt=ox.RdfFormat.N_TRIPLES, **kw) -> "GraphStore":
        """Build a store from serialized RDF text."""
        store = ox.Store()
        store.load(data, format=fmt)
        return cls(store, **kw)

    @classmethod
    def from_graph(cls, graph, **kw) -> "GraphStore":
        """Build a store from an :class:`rdflib.Graph`."""
        return cls.from_rdf(graph.serialize(format="nt"), **kw)

    @classmethod
    def from_bundle(cls, path: str | pathlib.Path, **kw) -> "GraphStore":
        """Build a store from a LOKF bundle directory or concept file."""
        from lokf import rdf

        return cls.from_graph(rdf.graph_of(path), **kw)

    def __len__(self) -> int:
        return len(self.store)

    # -- querying -----------------------------------------------------------
    def query(self, sparql: str, **kw):
        """Run a SPARQL query with the schema prefixes in scope.

        Returns pyoxigraph's native result: ``QuerySolutions`` (SELECT),
        ``QueryBoolean`` (ASK), or ``QueryTriples`` (CONSTRUCT/DESCRIBE).
        """
        return self.store.query(_prefix_header(self.prefixes) + sparql, **kw)

    def select(self, sparql: str, **kw) -> list[dict]:
        """Run a SELECT and return rows as ``{var: python value}`` dicts.

        Each binding is reduced to its lexical value (IRIs and literals become
        strings); unbound variables are omitted from a row.
        """
        result = self.query(sparql, **kw)
        variables = [str(v)[1:] for v in result.variables]  # strip leading '?'
        rows = []
        for solution in result:
            row = {}
            for var in variables:
                term = solution[var]
                if term is not None:
                    row[var] = term.value
            rows.append(row)
        return rows

    def ask(self, sparql: str, **kw) -> bool:
        """Run an ASK query and return the boolean."""
        return bool(self.query(sparql, **kw))

    def construct(self, sparql: str, fmt: str = "ttl", **kw) -> str:
        """Run a CONSTRUCT/DESCRIBE and serialize the resulting graph."""
        from lokf.rdf import _rdflib_format
        from rdflib import Graph

        triples = self.query(sparql, **kw)
        g = Graph()
        g.parse(data=triples.serialize(format=ox.RdfFormat.N_TRIPLES), format="nt")
        for prefix, ns in self.prefixes.items():
            g.bind(prefix, ns)
        data = g.serialize(format=_rdflib_format(fmt))
        return data if isinstance(data, str) else data.decode("utf-8")

    def serialize_results(self, sparql: str, fmt: str = "json", **kw) -> bytes:
        """Run a SELECT/ASK and serialize results in the SPARQL results format."""
        if fmt.lower() not in _RESULT_FORMATS:
            raise ValueError(
                f"unknown results format {fmt!r}; "
                f"choose from {', '.join(sorted(_RESULT_FORMATS))}"
            )
        return self.query(sparql, **kw).serialize(format=_RESULT_FORMATS[fmt.lower()])

    def rdflib_graph(self, sparql: str | None = None):
        """The store (or a CONSTRUCT/DESCRIBE result) as an :class:`rdflib.Graph`.

        With no query, the whole store is returned. This backs the live graph
        visualization, which projects the graph to cytoscape elements.
        """
        from rdflib import Graph

        if sparql is None:
            nt = self.store.dump(
                format=ox.RdfFormat.N_TRIPLES, from_graph=ox.DefaultGraph()
            )
        else:
            nt = self.query(sparql).serialize(format=ox.RdfFormat.N_TRIPLES)
        g = Graph()
        g.parse(data=nt, format="nt")
        for prefix, ns in self.prefixes.items():
            g.bind(prefix, ns)
        return g

    def dump(self, fmt=ox.RdfFormat.TURTLE) -> bytes:
        """Serialize the whole store (default graph) as RDF text."""
        return self.store.dump(format=fmt, from_graph=ox.DefaultGraph())
