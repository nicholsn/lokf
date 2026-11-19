---
title: MCP server
description: The lokf-mcp stdio server that lets an agent drive the toolkit over MCP.
sidebar:
  order: 6
---

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
| `get_vocabulary` | The selected schema vocabulary: `{classes, relations}`, or the full manifest with `all=true`. |
| `bundle_summary` | Orientation at a glance: `{concept_count, types, triple_count, relation_edge_count}`. |

Each tool takes a bundle or concept path (and, where relevant, a SPARQL string
or output format) and hands back structured data the agent can reason over.

## Discover a project's vocabulary

Use `get_vocabulary(bundle="/projects/example/knowledge")` to read the schema
declared by the project's nearest `[tool.lokf].schema` in `pyproject.toml`.
The path can also identify a concept file or project directory. An explicit
`schema="/schemas/domain.yaml"` takes precedence. Relative explicit paths use
the server's working directory; paths declared in a project are relative to
that project's `pyproject.toml`. Missing or malformed declarations are errors.

With neither selector, `get_vocabulary()` keeps its existing cwd/core lookup;
it does not implicitly switch to a project's declared domain. Existing calls
and response shapes, including `get_vocabulary(all=true)`, remain supported.
Short discovery includes custom relation slots as well as enum relations. When
both have the same name, the enum row keeps its existing meaning and description.
The full manifest continues to list documented slots; it is not a substitute
for validation against the schema.

`propose_relations` now uses its bundle's declared schema, with an optional
`schema` override. It recognizes existing custom references and inherited slot
domains. It still uses fixed prose cues; declaring a new predicate does not teach
it new cues. Its `apply` option still edits in place without general validation.

### Optional schema identity

`get_vocabulary(bundle="/projects/example/knowledge", include_metadata=true)`
adds `schema_metadata` to either response shape:

| Field | Meaning |
| --- | --- |
| `complete` | Whether all schema inputs were captured locally. |
| `revision` | `sha256:` digest of the canonical identity manifest, or `null` for live remote imports. |
| `format` | `lokf-schema-inputs-v1`. |
| `root_sha256` | SHA-256 of the root schema's exact bytes. |
| `sources` | Root and transitive dependencies, including packaged LinkML types; each has `id`, `sha256` and ordered direct-import hashes. |
| `linkml_runtime` | Runtime version used to interpret those inputs. |

The digest hashes UTF-8 JSON containing `format`, `root_sha256`, `sources` and
`linkml_runtime`, with sorted object keys and compact separators. Sources are
ordered by ID then hash; absolute local paths are excluded. Moving a project
without changing its inputs preserves the identity; editing a dependency changes
it even if the root, file sizes and timestamps stay the same.

Local schemas and contexts use bounded caches checked against source contents
on each read. Parsing and generation consume captured bytes. Concurrent source
changes detected during capture cause an error; callers can retry. This is a
schema-input identity, not an immutable document/graph snapshot or an identity
for a generated JSON-LD context. Context caches also depend on the core context
bytes, and the generator version is fixed for the running installation.

Closures larger than 256 files are rejected. Live remote imports retain their
existing reading behavior but bypass these caches. Their metadata contains
`complete=false`, `revision=null` and a `reason`, rather than claiming a complete
revision for sources the service did not capture. Project selectors do not grant
access: paths are interpreted with the server process's existing permissions.

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
[Agents](/toolkit/agents/).
