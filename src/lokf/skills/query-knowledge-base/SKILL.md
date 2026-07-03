---
name: query-knowledge-base
description: Answer a question about a LOKF bundle by writing SPARQL and running 'lokf query'. Use when you need to look up concepts, relations, counts, or provenance chains instead of reading files by hand.
---

# Query a LOKF knowledge base

## Purpose

`lokf query <bundle> "<sparql>"` loads a whole bundle into an in-memory RDF
store and answers SPARQL over it. It is the right way to ask precise questions
("which metrics depend on this table?", "what is derived from what?") rather
than grepping markdown.

## When to use

- Answering a factual question that spans multiple concepts.
- Producing a list, count, or provenance chain from the graph.
- Feeding results to another step as `json` / `csv` / `tsv`, or a `ttl`
  subgraph from a `CONSTRUCT`.

## Preset prefixes (no PREFIX block needed)

The store pre-declares the schema namespaces, so queries can use these CURIEs
directly:

`lokf:` `linkml:` `schema:` `dcat:` `dcterms:` `prov:` `skos:` `foaf:`
`rdf:` `rdfs:` `owl:` `xsd:` `pav:`

Concept types render as their class URI, e.g. a `Metric` is `lokf:Metric`, a
`Dataset` is `schema:Dataset`, a `Table` is `lokf:Table`. Typed relations use
the predicate from `lokf vocab` (e.g. `derivedFrom` → `prov:wasDerivedFrom`,
`dependsOn` → `dcterms:requires`, `measures` → `lokf:measures`).

## Output formats

`--format table` (default, human), `json`, `csv`, `tsv` for SELECT/ASK; a
CONSTRUCT/DESCRIBE emits `ttl` (or another RDF format). Example:
`lokf query <bundle> "SELECT ..." --format json`.

## Worked patterns

Run these against `examples/acme-knowledge`.

**1. Everything of a type** — list all metrics with their titles:

```bash
lokf query examples/acme-knowledge \
  "SELECT ?s ?title WHERE { ?s a lokf:Metric ; dcterms:title ?title }"
```

**2. Follow a relation** — what each concept depends on:

```bash
lokf query examples/acme-knowledge \
  "SELECT ?s ?target WHERE { ?s dcterms:requires ?target }"
```

(`dcterms:requires` is the `dependsOn` slot. Swap in `prov:wasDerivedFrom`
for `derivedFrom`, `schema:hasPart` for `hasPart`, `lokf:measures` for a
metric's `measures`.)

**3. Counts / aggregation** — how many concepts of each type:

```bash
lokf query examples/acme-knowledge \
  "SELECT ?type (COUNT(?s) AS ?n) WHERE { ?s a ?type } GROUP BY ?type ORDER BY DESC(?n)"
```

**4. Provenance chain** — trace a metric back to its source table via
`derivedFrom`, and check existence with ASK:

```bash
lokf query examples/acme-knowledge \
  "SELECT ?metric ?table WHERE { ?metric a lokf:Metric ; prov:wasDerivedFrom ?table }"

lokf query examples/acme-knowledge \
  "ASK { ?m a lokf:Metric ; prov:wasDerivedFrom ?t . ?t a lokf:Table }"
```

**5. Extract a subgraph** — CONSTRUCT one concept's outgoing edges as Turtle:

```bash
lokf query examples/acme-knowledge \
  "CONSTRUCT { ?s ?p ?o } WHERE { ?s a lokf:Metric ; ?p ?o }" --format ttl
```

## Method

1. Restate the question as: which subjects, which predicate(s), which objects.
2. Map English relation names to CURIEs via `lokf vocab` (name → curie column).
3. Start with a broad `SELECT ?s ?p ?o WHERE { <focus> ?p ?o }` to see what
   predicates a concept actually has, then tighten the pattern.
4. Choose `--format json`/`csv` when piping the answer onward.

## Done when

- The query returns exactly the rows that answer the question, and you have
  confirmed the predicate CURIEs against `lokf vocab`.
