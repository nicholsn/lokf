---
name: build-knowledge-base
description: Build a LOKF knowledge base end-to-end — create the index, author concepts, enrich relations, validate, and query. Use when starting a new bundle from scratch or standing up a knowledge base for a domain.
---

# Build a LOKF knowledge base end-to-end

## Purpose

This is the umbrella workflow. It ties together the focused skills
(`author-concept`, `enrich-relations`, `query-knowledge-base`,
`publish-graph`) into a full path from an empty directory to a validated,
queryable knowledge graph.

## When to use

- Standing up a brand-new bundle for a team, product, or domain.
- Migrating scattered docs/specs into one canonical, agent-readable KB.

## What a bundle is

A directory containing an `index.md` (the bundle manifest) plus one markdown
file per concept, grouped into subdirectories by type (`metrics/`, `datasets/`,
`tables/`, `glossary/`, `services/`, `playbooks/`). The toolkit reads the whole
directory as one RDF graph.

## Steps

1. **Create the bundle `index.md`.** This declares the `base_iri` (every
   concept `id` hangs off it), the JSON-LD `context`, publisher, and license,
   and lists the concepts. Start minimal:

   ```markdown
   ---
   lokf_version: "0.1"
   okf_version: "0.1"
   base_iri: https://acme.example/knowledge/
   context: https://w3id.org/lokf/context.jsonld
   title: Acme Knowledge Bundle
   description: Canonical, agent-readable knowledge for Acme.
   license: https://creativecommons.org/licenses/by/4.0/
   publisher:
     type: Organization
     id: https://acme.example
     name: Acme Corp
   ---

   # Metrics
   # Datasets
   # Glossary
   # Services
   # Playbooks
   ```

   The `base_iri` is load-bearing: a concept at `metrics/wau.md` gets id
   `<base_iri>metrics/wau`.

2. **Author the concepts.** For each concept, follow the `author-concept`
   skill: pick the right `type`, write frontmatter (`type`/`id`/`title`/
   `description`/`timestamp` plus type-specific fields), write a body with
   headings, link to sibling concepts in prose, and add a bullet for it under
   the matching `index.md` heading. Author foundational concepts first
   (glossary terms, tables) so later ones can reference them.

3. **Check the vocabulary** so you use real relation names and know which types
   support which slots:

   ```bash
   lokf vocab
   ```

4. **Enrich relations** — upgrade the prose links you wrote into typed edges
   (the `enrich-relations` skill). Dry-run, set a confidence floor, then apply:

   ```bash
   lokf propose <bundle>
   lokf propose <bundle> --min-confidence 0.6 --apply
   ```

   Review the frontmatter diff before keeping it.

5. **Validate** the whole bundle renders to RDF without errors, and spot-check
   the triple set:

   ```bash
   lokf convert <bundle> --format ttl | tail -20
   ```

   Every concept should appear with its `type`, `title`, and typed relations.

6. **Query it** to confirm the graph answers real questions (the
   `query-knowledge-base` skill):

   ```bash
   lokf query <bundle> \
     "SELECT ?type (COUNT(?s) AS ?n) WHERE { ?s a ?type } GROUP BY ?type"
   lokf query <bundle> \
     "SELECT ?m ?t WHERE { ?m a lokf:Metric ; prov:wasDerivedFrom ?t }"
   ```

7. **Publish** for interactive exploration or programmatic access (the
   `publish-graph` skill):

   ```bash
   lokf serve <bundle>
   ```

## Iteration loop

Adding knowledge is: author-concept → enrich-relations → validate → query.
Repeat as the domain grows; keep `index.md` in sync with the files on disk.

## Done when

- `lokf convert <bundle>` succeeds and includes every concept.
- The intended typed relations exist (visible in frontmatter and in the RDF).
- Representative `lokf query` questions return correct answers.
- `lokf serve <bundle>` renders the graph.
