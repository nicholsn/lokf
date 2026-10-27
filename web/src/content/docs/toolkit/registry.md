---
title: Registry
description: Federate bundles with lokf registry, one manifest and one named graph per member, with SPARQL and an MCP server across all of them.
sidebar:
  order: 10
---

A **registry** is a manifest of LOKF bundles. `lokf registry` loads each
member into its own named graph, named by the member's `base_iri`. It then
answers SPARQL across all of them, resolves any concept IRI to the bundle that
owns it, and serves the federation to people and to agents. The format is
[SPEC §11](/specification/#11-federation-registries-of-bundles); this page
is the commands.

## What a member publishes

A member runs [`lokf export`](/toolkit/) and serves the four files it
writes, the *producer contract* a registry harvests:

```bash
lokf export knowledge --out-dir public --source-base https://github.com/acme/knowledge/tree/main/knowledge
```

| File | What a registry does with it |
|---|---|
| `graph.nt` | loads it into the member's named graph |
| `concepts.jsonld` | reads a foreign concept's source document offline |
| `datasets.jsonld` | schema.org `Dataset` descriptions, for search engines |
| `graph.json` | the graph explorer's nodes and edges |

## Register members

`init` writes an empty manifest, with `--id` and `--title` for the
catalogue's IRI and name. `add` registers a bundle from a local directory, a
bundle zip, or the URL of one, deriving its `base_iri`, VoID counts and the
index of explicit `id`s. `list` prints the routing table. Every
`lokf registry` command works on `lokf-registry.yaml` in the current
directory; `-r` names another manifest.

```bash
lokf registry init
# -> wrote lokf-registry.yaml
lokf registry add acme --source-base https://github.com/nicholsn/lokf/tree/main/examples/acme-knowledge
# -> registered https://acme.example/knowledge/ (157 triples) in lokf-registry.yaml
lokf registry list
# -> https://acme.example/knowledge/  Acme Knowledge Bundle  157 triples  ok
```

The manifest is a `dcat:Catalog`; each entry is a `void:Dataset` keyed by its
`base_iri`:

```yaml
lokf_registry_version: '0.1'
type: dcat:Catalog
repos:
- base_iri: https://acme.example/knowledge/
  title: Acme Knowledge Bundle
  source_base: https://github.com/nicholsn/lokf/tree/main/examples/acme-knowledge
  path: acme
  void:
    triples: 157
    class_partition:
      AttestedComputation: 1
      Dataset: 1
      GlossaryTerm: 1
      Metric: 1
      Playbook: 1
      Reference: 1
      Service: 1
      Table: 1
```

Two `base_iri`s may not nest, so at most one member owns any IRI. A zip is
registered with its `--checksum`, and `--archive-url` records where it is
published in place of a local path. An explicit `id` outside the bundle's own
namespace is refused unless `--allow-foreign-ids` is given.

## Resolve an IRI

`resolve` routes an IRI to its owning member by longest `base_iri` prefix. It
reads no bundle, and fetches nothing unless the tree names a sub-registry by
URL:

```bash
lokf registry resolve https://acme.example/knowledge/metrics/weekly-active-users
# https://acme.example/knowledge/metrics/weekly-active-users
#   owner:      https://acme.example/knowledge/ (Acme Knowledge Bundle)
#   concept_id: metrics/weekly-active-users
#   source_url: https://github.com/nicholsn/lokf/tree/main/examples/acme-knowledge/metrics/weekly-active-users.md
#   via:        prefix
```

It exits non-zero for an IRI no member owns: a dangling cross-link the
federation tolerates.

## Build, query and serve the federation

`build` loads every member into its named graph and writes the union as
N-Quads, reporting each relation target that no member owns or that its
owner does not hold. `--strict` fails the build when a member cannot be
loaded or a target does not resolve.

```bash
lokf registry build --out-dir out
# -> wrote out/federation.nq (157 quads, 1 of 1 members)
# -> unowned: https://wiki.acme.example/rfc/metric-defs (asserted in https://acme.example/knowledge/ via http://www.w3.org/2000/01/rdf-schema#isDefinedBy)
```

`query` runs SPARQL over all members at once, the default graph being their
union; `GRAPH ?g` binds a member's `base_iri`, so a result says which bundle
asserted it:

```bash
lokf registry query 'SELECT ?g (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g'
# g                                n
# https://acme.example/knowledge/  157
```

`serve` publishes the same store as a SPARQL endpoint with the graph
explorer, as [`lokf serve`](/toolkit/serve/) does for one bundle. `query`,
`serve` and `mcp` take `--quads out/federation.nq` to load a built snapshot
instead of fetching the members again.

## For agents

`lokf registry mcp` runs the `lokf-registry` MCP server over stdio, with five
tools, each bounded in depth and breadth so a cross-bundle hop is one call:
`resolve_iri`, `neighbors`, `subgraph`, `federated_sparql` and
`read_document`. The registry's index is the server's instructions;
`--index` substitutes a Markdown file of your own.

## Sensitive members and registries of registries

A member whose entry carries a `sensitivity` other than `public` is skipped
before its content is read. The registry's owner clears one for a run with
`--clear-member IRI` on `build`, `query`, `serve` or `mcp`; clearance is never
written into the manifest, and a prebuilt N-Quads file is loaded as supplied.

An entry of `type: dcat:Catalog` names another registry. `build`, `query`,
`serve`, `mcp` and `resolve` follow it, tier by tier, to the top registry's
`max_depth`, skip a registry they cannot read, and take only URLs from a
manifest fetched by URL.
