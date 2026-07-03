# MCP server

LOKF ships a [Model Context Protocol](https://modelcontextprotocol.io) server
so an agent can drive the toolkit directly — load a bundle, run SPARQL,
project RDF, propose relations — without shelling out to the CLI or parsing
its text output. Every tool returns JSON-serializable values.

## Running it

The server speaks MCP over **stdio**. Two equivalent ways to launch it:

```bash
uv run lokf mcp     # the CLI subcommand
lokf-mcp            # the dedicated console script (same server)
```

`lokf-mcp` is the entry point you point an MCP client at, because a client
launches the server as a subprocess and talks to it over stdin/stdout.

## Client configuration

Most MCP clients read an `mcpServers` block. Register `lokf-mcp` as the
command:

```json
{
  "mcpServers": {
    "lokf": {
      "command": "lokf-mcp"
    }
  }
}
```

If `lokf` is installed in a project virtualenv rather than on the global
`PATH`, run it through `uv` instead:

```json
{
  "mcpServers": {
    "lokf": {
      "command": "uv",
      "args": ["run", "lokf-mcp"]
    }
  }
}
```

## The tools

The server exposes seven tools, mirroring the toolkit surface. Each returns
JSON-serializable data (and a `{"error": …}` object on bad input rather than
throwing):

| Tool | What it does |
|---|---|
| `list_concepts` | Fast index of a bundle: `{concept_id, type, title, iri}` for every concept. |
| `describe_concept` | Full record of one concept — `{iri, type, title, body, frontmatter, turtle}`. |
| `sparql_query` | Run SPARQL over the bundle. SELECT → `{columns, rows}`, ASK → `{boolean}`, CONSTRUCT/DESCRIBE → `{turtle}`. Schema prefixes preset. |
| `convert` | Project a concept file or bundle directory to RDF: `{format, rdf}` (`ttl`, `nt`, `jsonld`, …). |
| `propose_relations` | Suggest typed relations from prose links; optionally `apply` them, with a per-proposal `applied` flag. |
| `get_vocabulary` | The schema vocabulary: `{classes, relations}` read from `lokf.yaml`. |
| `bundle_summary` | Orientation at a glance: `{concept_count, types, triple_count, relation_edge_count}`. |

Each tool takes a bundle or concept path (and, where relevant, a SPARQL string
or output format) and hands back structured data the agent can reason over.

## What agents can automate

With the server connected, an agent can run an end-to-end loop over a knowledge
base with no bespoke code:

- **Orient** — call `bundle_summary` and `list_concepts` to learn what a
  knowledge base holds before touching it.
- **Author-and-check** — write a concept, `convert` it (or read its `turtle`
  from `describe_concept`), and `sparql_query` the graph to confirm the new
  triples landed on the right subjects.
- **Enrich** — call `propose_relations` to surface typed edges the prose already
  implies, review the confidence and rationale, and apply the ones worth
  keeping.
- **Answer questions** — turn a natural-language question into a `sparql_query`
  against the bundle and read back the rows.
- **Stay schema-correct** — call `get_vocabulary` to discover which relations a
  class is allowed to use.

For the skills that package these workflows for coding agents, see
[Agents](agents.md).
