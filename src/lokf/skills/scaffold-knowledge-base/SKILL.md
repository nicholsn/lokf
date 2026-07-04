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

   This creates `my-kb/` with a starter bundle (`knowledge/`), a MkDocs site, a
   GitHub Pages workflow, a `justfile`, and these skills under `.claude/skills/`.

2. **Understand the domain.** Ask the human what concepts matter and how they
   relate. Sketch the types (`Metric`, `Dataset`, `Table`, `GlossaryTerm`,
   `Service`, `Playbook`, `Document`, `Reference`, `Person`, `Organization`,
   `Role`) and the typed relations between them (`measures`, `dependsOn`,
   `derivedFrom`, `isPartOf`, `about`, `memberOf`, …).

3. **Author the concepts.** Delete the two examples under `knowledge/` and use
   the `author-concept` skill to write one file per concept, then
   `enrich-relations` to type the links. Register each concept in
   `knowledge/index.md`.

4. **Validate.** Project the bundle to RDF to confirm it parses and the typed
   relations bind to the right predicates:

   ```bash
   uvx --from lokf lokf convert knowledge --format ttl | tail
   ```

   Explore it interactively with `just serve`; get the tabular projection with
   `just tables`.

5. **Publish.** Set `base_iri` in `knowledge/index.md` to the real URL, commit,
   push to GitHub, and set **Settings → Pages → Source** to **GitHub Actions**.
   The `pages` workflow builds and deploys on every push to `main`.

## Done when

- `lokf convert knowledge --format ttl` emits the intended concepts and edges.
- Every concept is listed in `knowledge/index.md`.
- The repo is pushed and the Pages workflow has published the site.
