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

Use a bundle directory on the server's filesystem for `bundle`. In
`describe_concept`, `concept_id` is a path relative to the bundle, such as
`metrics/weekly-active-users`. Tools take named JSON arguments. Optional
arguments below show their defaults.

| Tool and arguments | Result |
| --- | --- |
| `list_concepts(bundle)` | One row per concept with `concept_id`, `type`, `title`, `iri`, lifecycle `status` and `trust_tier`. |
| `describe_concept(bundle, concept_id)` | IRI, type, title, Markdown body, frontmatter, trust summary and Turtle projection. |
| `sparql_query(bundle, query)` | SELECT returns `columns` and `rows`, ASK returns `boolean`, and CONSTRUCT or DESCRIBE returns `turtle`. Schema prefixes are preset. |
| `convert(source, format="ttl")` | A concept file or bundle as RDF, with `format` and `rdf`. Formats include `ttl`, `nt`, `jsonld`, `xml`, `n3` and `trig`. |
| `propose_relations(bundle, min_confidence=0.0, apply=false, schema=null)` | Typed relations suggested from prose links, with confidence and rationale. With `apply=true`, writes accepted proposals to frontmatter and reports `applied` for each row. |
| `get_vocabulary(all=false, bundle=null, schema=null, include_metadata=false)` | Class CURIEs and relation rows. Use `all=true` for the manifest of classes, slots and enums. |
| `validate_bundle(bundle, schema=null, check_ids=false, check_refs=false, check_resources=false, check_excerpts=false, shacl=false, root=null, max_diagnostics=50)` | Content verdict, check statuses, located diagnostics and coverage of local evidence. |
| `bundle_summary(bundle)` | Concept, triple and relation-edge counts, counts by type and trust tier, and a stale-concept count. |

To query several bundles together, use the [registry MCP server](/toolkit/registry/#for-agents).

## Validate a bundle

Call `validate_bundle(bundle="/project/knowledge", check_ids=true, check_refs=true,
shacl=true)` to check content against its declared vocabulary. The optional
`schema`, `check_resources`, `check_excerpts` and `root` arguments mirror
`lokf validate`. Install `lokf[build]` for validation and `lokf[shacl]` for SHACL.

- `outcome` is `valid`, `invalid` or `incomplete`. A confirmed content error
  yields `invalid` even if a later check cannot finish. A missing validator yields
  `incomplete` when no content error has been established. If a bundle directory
  cannot be scanned, the input check is unavailable and the concept count is null.
- `checks` records each check as `passed`, `failed`, `unavailable`, `skipped`
  (selected but never reached) or `disabled`. Warnings alone permit a pass.
  Reference checks find missing local targets. SHACL also checks target classes.
- Each diagnostic carries a stable `code`, `severity`, check name and message.
  Where available, `document` is bundle-relative, `field` is a JSON Pointer for
  the authored frontmatter or a predicate IRI for RDF, and `line` starts at 1.
  A SHACL finding can have a null document when several files declare its subject. Use
  `max_diagnostics` (1–100, default 50) to limit the response. `diagnostic_count`
  counts all findings and `omitted` counts those beyond the limit. Text fields
  are capped at 512 characters. The limit applies only to the displayed findings.
- `excerpts` and `resources` give local, remote and unchecked counts when those
  checks run. Remote evidence is never fetched. For excerpts, `local` counts
  comparisons actually performed. An unreadable evidence file counts as
  `unchecked` and makes the excerpt check `unavailable`. A binary file also
  counts as `unchecked` and produces a content error because a quote needs text.
  Resource counts refer to authored resource entries. An inaccessible path or
  glob directory makes the resource check unavailable. A missing path or a
  fully scanned pattern with no matches produces a content error.
- `schema.revision` identifies the captured local schema and imports. It is
  null with a reason when unavailable. `source.kind` is `live_bundle` and
  `source.revision` is null. A second call can observe edits to Markdown or cited
  files. A validation report describes one run and grants no write permission.

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
  implies, review the confidence and rationale, and pass `min_confidence`
  and `apply=true` to write proposals at or above the chosen threshold.
- **Answer questions** — turn a natural-language question into a `sparql_query`
  against the bundle and read back the rows.
- **Stay schema-correct** — call `get_vocabulary` to discover the classes and relations a
  project defines.

For the skills that package these workflows for coding agents, see
[Agents](/toolkit/agents/).
