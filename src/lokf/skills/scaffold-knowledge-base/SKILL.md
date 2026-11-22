---
name: scaffold-knowledge-base
description: Scaffold and publish a brand-new LOKF knowledge base from an idea — run `lokf new` to create the repo, author the concepts, validate, and publish to GitHub Pages. Use when someone describes a knowledge base they want to exist but there is no repo yet.
---

# Scaffold a knowledge base from an idea

## Purpose

Go from a one-line idea ("a knowledge base of our data metrics", "my research
group's methods and datasets") to a published LOKF site. This skill scaffolds
the repository, then hands off to `author-concept` / `build-knowledge-base` /
`enrich-relations` to fill it in.

## When to use

- There is no repo yet and someone wants a knowledge base to exist.
- Turning a domain, product, team, or personal corpus into a published,
  queryable knowledge graph *and* website.

## Steps

1. **Scaffold the repo.** Pick a short kebab-case name and, if known, the URL it
   will publish to:

   ```bash
   lokf new my-kb --title "My Knowledge Base" --base-iri https://myorg.github.io/my-kb/
   ```

   This creates `my-kb/` with a starter bundle (`knowledge/`), a full Astro
   site with concept pages, a graph explorer at `/graph`, a schema browser
   at `/schema`, and a JSON-LD projection at `/graph.jsonld`,
   a GitHub Pages workflow, a `justfile`, and these skills under
   `.claude/skills/`. Pass the real published URL as `--base-iri` when known —
   it configures both the concept IRIs and the site's base path.

2. **Understand the domain.** Identify the reader's first question, the concept
   they would start from, and the typed relations leading to an answer. If the
   project defines its own LinkML vocabulary, declare its path under
   `[tool.lokf]` as `schema = "schema/my-domain.yaml"` in `pyproject.toml`.
   From the new repo, run `lokf vocab --bundle knowledge --all` to see the
   available classes and slots.

3. **Author the concepts.** Adapt or replace the two examples under `knowledge/` and use
   the `author-concept` skill to write one file per concept, then
   `enrich-relations` to type the links. Register each concept in
   `knowledge/index.md`.

4. **Configure a reader's starting point.** For a guided view, copy
   `lokf.views.example.yaml` to `lokf.views.yaml` at the repo root. Set
   `roots.type` to the entry class and follow its relations in a section's
   `path`. Choose a list, table, or dated timeline to answer the question.

   ```bash
   just validate
   just rdf
   just setup
   just dev
   ```

   For each configured view, check a path from the home page to a root, then a section
   member and its **Appears in** link back to the row. Use the **Schema** tab
   to check the class and relation definitions. Run `just site` to generate
   the static pages in `dist/`.

5. **Publish.** Confirm the base IRI matches the real URL everywhere it is
   held — `base_iri` in `knowledge/index.md`, `site`/`base` (and the
   `remarkLokfLinks` `base`) in `astro.config.mjs`, `BASE_IRI` in
   `src/lib/lokf.ts`, and the starter concept's `measures:` cross-reference —
   then commit
   `package-lock.json`, push to GitHub, and set **Settings → Pages → Source**
   to **GitHub Actions**. The `pages` workflow builds and deploys on every
   push to `main`.

## Done when

- `lokf convert knowledge --format ttl` emits the intended concepts and edges.
- Every concept is listed in `knowledge/index.md`.
- The repo is pushed and the Pages workflow has published the site.
