# Python reference

The `lokf` package is the LOKF toolkit: the bundle model (`lokf.model`), the
RDF projection (`lokf.rdf`), the SPARQL store (`lokf.store`), the local server
(`lokf.server`), the schema vocabulary (`lokf.schema`), the parsing helpers
(`lokf.parse`), the [relation proposer](../toolkit/proposer.md)
(`lokf.propose`), the graph and JSON-LD exporters (`lokf.export`), the
[MCP server](../toolkit/mcp.md) (`lokf.mcp_server`), and the `lokf-build`
console script that regenerates every artifact from `lokf.yaml`
(`lokf.build`). The same surface is available from the command line:
`lokf convert` / `query` / `serve` / `propose` / `vocab` / `skills` / `mcp`.
For a guided walkthrough, start with the
[Toolkit overview](../toolkit/index.md).

::: lokf.parse

::: lokf.build

The bundle model — `load_bundle()` and the `Bundle`/`Concept` objects it
returns, including the JSON-LD and `rdflib.Graph` projections.

::: lokf.model

RDF projection — `serialize()` and `graph_of()` turn a concept file or bundle
directory into RDF (the engine behind [`lokf convert`](../toolkit/convert.md)).

::: lokf.rdf

The SPARQL store — `GraphStore`, an in-memory pyoxigraph store with the schema
prefixes preset (the engine behind [`lokf query`](../toolkit/query.md)).

::: lokf.store

The local server — `serve()` / `build_server()` publish a bundle as a SPARQL
endpoint plus graph explorer (the engine behind
[`lokf serve`](../toolkit/serve.md)).

::: lokf.server

The vocabulary — typed-relation slots, the `RelationType` enum, and
CURIE/IRI helpers, all read from the LinkML schema rather than hardcoded.

::: lokf.schema

The relation proposer — turns prose links into typed-relation proposals and
applies accepted ones back into frontmatter (the `lokf propose` CLI).

::: lokf.propose

The exporters — Cytoscape.js graph elements and schema.org `Dataset` JSON-LD
for dataset-search markup.

::: lokf.export

The MCP server — exposes the toolkit as [MCP tools](../toolkit/mcp.md) over
stdio (`lokf mcp` / `lokf-mcp`) so agents can drive it.

::: lokf.mcp_server
