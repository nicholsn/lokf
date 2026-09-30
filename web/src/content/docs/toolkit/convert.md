---
title: Convert
description: Project LOKF markdown to RDF with lokf convert.
sidebar:
  order: 2
---

`lokf convert` projects LOKF markdown to RDF. It is the CLI in front of
[`lokf.rdf.serialize`](/reference/api/): attach the generated context,
expand the JSON-LD, and emit triples — no glue code on your side.

```bash
uv run lokf convert examples/acme-knowledge/metrics/weekly-active-users.md --format ttl
```

## Single file vs. bundle

`convert` takes either a **concept file** or a **bundle directory**.

- Point it at one `.md` file and it emits just that concept's triples. IRIs
  are still resolved against the enclosing bundle, so relative links land on
  the right subjects.
- Point it at the bundle directory (`examples/acme-knowledge`) and it projects
  every concept at once — the whole graph in one document.

```bash
# one concept
uv run lokf convert examples/acme-knowledge/glossary/active-user.md

# the whole bundle
uv run lokf convert examples/acme-knowledge --format nt
```

## Formats

`--format` / `-f` selects the serialization (default `ttl`):

| Value | Serialization |
|---|---|
| `ttl` | Turtle |
| `nt` | N-Triples |
| `jsonld` | JSON-LD |
| `xml` | RDF/XML |
| `n3` | Notation3 |
| `trig` | TriG |

## Writing to a file

By default `convert` streams to stdout. `--output` / `-o` writes to a file
instead:

```bash
uv run lokf convert examples/acme-knowledge --format nt --output acme.nt
# wrote acme.nt
```

## A domain schema

A bundle that validates with `lokf validate --schema` takes the same file here:

```bash
uv run lokf convert knowledge --schema domain.yaml
```

Or declare it once as `[tool.lokf] schema = "domain.yaml"` in the project's
`pyproject.toml` above the bundle, and `convert`, `query`, `serve`, `export`,
`validate` and the MCP server all read it.

The graph then uses a JSON-LD context generated from that schema. Its classes
and slots project under their own IRIs instead of as `lokf:` terms, and its
classes count as declared instead of reading as `lokf:Concept`. A key neither
schema declares still projects as a `lokf:` term, as it does without
`--schema`. Generating the context needs the `build` extra (`lokf[build]`).

## The `just` recipe

The `just gen-rdf-turtle` recipe wraps the Turtle case so it is one word to
type and easy to remember:

```bash
just gen-rdf-turtle examples/acme-knowledge/metrics/weekly-active-users.md
```

It runs `uv run lokf convert --format ttl {{FILE}}` — read-only, safe to run
against any concept or bundle.

## From Python

The CLI is a thin wrapper. In code, call the same function directly:

```python
from lokf import rdf

# a concept file or a bundle directory — either works
print(rdf.serialize("examples/acme-knowledge", "ttl"))

# or get an rdflib.Graph to keep working with
g = rdf.graph_of("examples/acme-knowledge/metrics/weekly-active-users.md")
len(g)
```

See [Markdown to RDF](/guide/markdown-to-rdf/) for the mechanics of the
projection, and [Query](/toolkit/query/) to run SPARQL over the result.
