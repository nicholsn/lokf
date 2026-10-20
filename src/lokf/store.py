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
import re

import pyoxigraph as ox

from lokf.schema import vocabulary

# SPARQL results short names -> pyoxigraph result format.
_RESULT_FORMATS = {
    "json": ox.QueryResultsFormat.JSON,
    "xml": ox.QueryResultsFormat.XML,
    "csv": ox.QueryResultsFormat.CSV,
    "tsv": ox.QueryResultsFormat.TSV,
}

# The query form, skipping any leading comments and PREFIX/BASE declarations,
# whether each sits on a line of its own or they share one with the query.
_QUERY_FORM = re.compile(
    r"^(?:\s+|#[^\n]*|prefix\s+[^\s:]*:\s*<[^>]*>|base\s*<[^>]*>)*"
    r"(select|ask|construct|describe)\b",
    re.IGNORECASE,
)

# Strings, IRIs and comments: where the word "service" is not the keyword.
# Matched in one pass, so a '#' inside an IRI or a string is not a comment.
_SPARQL_NOT_CODE = re.compile(
    r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\''
    r'|<[^<>"{}|^`\\\x00-\x20]*>|#[^\n]*'
)
# The keyword, as opposed to a variable (?service), a prefixed name
# (ex:service, service:x) or part of a longer name.
_SERVICE_KEYWORD = re.compile(r"(?<![\w?$:.\-])service(?![\w:.\-])", re.IGNORECASE)


def query_form(sparql: str) -> str:
    """The SPARQL query form: 'select', 'ask', 'construct', or 'describe'.

    Leading comments and PREFIX/BASE lines are skipped. Defaults to 'select'
    when no form keyword is found. Shared by the CLI, server, and MCP so all
    three classify a query identically.
    """
    m = _QUERY_FORM.match(sparql)
    return m.group(1).lower() if m else "select"


def _prefix_header(prefixes: dict[str, str]) -> str:
    return "".join(f"PREFIX {p}: <{ns}>\n" for p, ns in prefixes.items())


def _uses_service(sparql: str) -> bool:
    """True if the query contains a SPARQL ``SERVICE`` (federation) clause.

    Parsed via rdflib's algebra so a ``SERVICE`` inside a string literal does
    not trip it. Oxigraph accepts syntax rdflib does not (RDF 1.2 triple
    terms, for one), so a query rdflib cannot parse is not trusted to be
    free of ``SERVICE``: a scan of its text outside strings, IRIs and comments
    decides, and finds the keyword wherever it could be one. Failing closed
    is the point; a query with no such word still reaches the engine, which
    judges its validity.
    """
    # SERVICE is the only spelling of the federation keyword, so a query with
    # no "service" substring cannot contain one — skip the ~1ms parse. (A
    # "service" inside a string literal still falls through to the algebra
    # walk, which correctly ignores it.)
    if "service" not in sparql.lower():
        return False

    from rdflib.plugins.sparql import prepareQuery
    from rdflib.plugins.sparql.parserutils import CompValue

    try:
        algebra = prepareQuery(sparql).algebra
    except Exception:  # noqa: BLE001 — rdflib's limits are not the engine's
        return bool(_SERVICE_KEYWORD.search(_SPARQL_NOT_CODE.sub(" ", sparql)))

    def walk(node) -> bool:
        if isinstance(node, CompValue):  # note: CompValue is itself a dict
            return node.name == "ServiceGraphPattern" or any(map(walk, node.values()))
        if isinstance(node, (list, tuple, set)):
            return any(map(walk, node))
        if isinstance(node, dict):
            return any(map(walk, node.values()))
        return False

    return walk(algebra)


class GraphStore:
    """An in-memory SPARQL store over a LOKF knowledge base.

    ``prefixes`` (the schema's namespace table) are prepended to every query
    and update, so ``lokf:``/``schema:``/``prov:`` and friends work without a
    per-query ``PREFIX`` block.

    A store built from a registry holds one named graph per member and sets
    ``union``: queries then read the default graph as the union of all of
    them, and ``GRAPH ?g`` still names the member that asserted a triple.
    """

    def __init__(
        self,
        store: ox.Store,
        prefixes: dict[str, str] | None = None,
        union: bool = False,
    ):
        self.store = store
        self.prefixes = prefixes if prefixes is not None else vocabulary().prefixes
        self.union = union
        #: base_iri -> why that member could not be loaded (registry stores only).
        self.load_errors: dict[str, str] = {}

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
    def from_bundle(
        cls, path: str | pathlib.Path, schema: str | pathlib.Path | None = None, **kw
    ) -> "GraphStore":
        """Build a store from a LOKF bundle directory or concept file, under
        the domain *schema* when one is given. Queries then also get that
        schema's prefixes."""
        from lokf import rdf

        if schema is not None:
            kw.setdefault("prefixes", vocabulary(schema).prefixes)
        return cls.from_graph(rdf.graph_of(path, schema=schema), **kw)

    @classmethod
    def from_registry(cls, registry, **kw) -> "GraphStore":
        """Build a store holding each registry member in a named graph whose
        IRI is its ``base_iri`` (SPEC §11.4).

        *registry* is a :class:`lokf.registry.Registry` or a manifest path. A
        member that cannot be loaded is skipped and its reason kept in
        :attr:`load_errors`, so one unreachable member does not stop the rest.
        Blank-node labels are prefixed per member, so two members' nodes never
        merge and the same inputs always give the same labels.
        """
        import hashlib

        from lokf.registry import load_registry, member_ntriples

        if not hasattr(registry, "repos"):
            registry = load_registry(registry)
        store = ox.Store()
        errors: dict[str, str] = {}
        for entry in registry.repos:
            try:
                nt = member_ntriples(entry)
            except (ValueError, OSError) as exc:
                errors[entry.base_iri] = str(exc)
                continue
            graph = ox.NamedNode(entry.base_iri)
            tag = "m" + hashlib.sha256(entry.base_iri.encode()).hexdigest()[:12] + "_"

            def local(term, tag=tag):
                return ox.BlankNode(tag + term.value) if isinstance(term, ox.BlankNode) else term

            store.extend(
                ox.Quad(local(t.subject), t.predicate, local(t.object), graph)
                for t in ox.parse(nt, format=ox.RdfFormat.N_TRIPLES)
            )
        out = cls(store, union=True, **kw)
        out.load_errors = errors
        return out

    @classmethod
    def from_quads(cls, data: str | bytes, **kw) -> "GraphStore":
        """Build a union store from N-Quads, such as ``lokf registry build`` writes."""
        store = ox.Store()
        store.load(data, format=ox.RdfFormat.N_QUADS)
        return cls(store, union=True, **kw)

    def __len__(self) -> int:
        return len(self.store)

    # -- querying -----------------------------------------------------------
    def query(self, sparql: str, **kw):
        """Run a SPARQL query with the schema prefixes in scope.

        Returns pyoxigraph's native result: ``QuerySolutions`` (SELECT),
        ``QueryBoolean`` (ASK), or ``QueryTriples`` (CONSTRUCT/DESCRIBE).

        Federated ``SERVICE`` queries are rejected: the engine would issue an
        outbound request to a query-controlled host, which is an SSRF vector
        for the local ``lokf serve`` endpoint. (``LOAD``/``INSERT``/``DELETE``
        are already rejected by pyoxigraph's read-only ``query``.)
        """
        full = _prefix_header(self.prefixes) + sparql
        if _uses_service(full):
            raise ValueError(
                "SPARQL SERVICE (federated query) is disabled: it would let a "
                "query drive outbound network requests"
            )
        if self.union:
            kw.setdefault("use_default_graph_as_union", True)
        return self.store.query(full, **kw)

    def select(self, sparql: str, **kw) -> list[dict]:
        """Run a SELECT and return rows as ``{var: python value}`` dicts.

        Every selected variable is a key in every row (``None`` when unbound),
        so the column set is complete even when a variable is unbound in all
        rows; bound bindings are reduced to their lexical value.
        """
        result = self.query(sparql, **kw)
        variables = [v.value for v in result.variables]
        rows = []
        for solution in result:
            rows.append(
                {
                    var: (solution[var].value if solution[var] is not None else None)
                    for var in variables
                }
            )
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

        With no query, the whole store is returned (the union of its named
        graphs for a registry store). This backs the live graph visualization,
        which projects the graph to cytoscape elements.
        """
        from rdflib import Graph

        if sparql is None and self.union:
            nt = self.query("CONSTRUCT WHERE { ?s ?p ?o }").serialize(
                format=ox.RdfFormat.N_TRIPLES
            )
        elif sparql is None:
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
        """Serialize the whole store as RDF text: the default graph, or for a
        registry store every named graph (a dataset format such as N-Quads)
        or their union (a triple format)."""
        if not self.union:
            return self.store.dump(format=fmt, from_graph=ox.DefaultGraph())
        if fmt.supports_datasets:
            return self.store.dump(format=fmt)
        return self.query("CONSTRUCT WHERE { ?s ?p ?o }").serialize(format=fmt)
