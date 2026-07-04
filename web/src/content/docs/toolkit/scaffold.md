---
title: Scaffold a knowledge base (lokf new)
description: Create a new, publishable LOKF knowledge base — bundle, Astro site with the graph browser, and agent skills — with one command.
---

`lokf new <name>` scaffolds a complete, publishable knowledge base — in the
spirit of linkml-cookiecutter. One command, and you (or an AI agent) can go from
an idea to a queryable knowledge graph *and* a full website with the
interactive **graph browser**.

## Command

```bash
lokf new my-kb --title "My Knowledge Base" --base-iri https://myorg.github.io/my-kb/
```

Creates `my-kb/`:

```
my-kb/
  knowledge/                     # the LOKF bundle (index.md + example concepts)
  src/                           # the Astro site
    pages/index.astro            #   home: concepts grouped by type
    pages/[...slug].astro        #   one page per concept, with relations panels
    pages/graph.astro            #   the interactive graph browser
    pages/graph.json.ts          #   nodes + edges for the browser
    pages/graph.jsonld.ts        #   the whole bundle as JSON-LD (the RDF view)
  package.json · astro.config.mjs · tsconfig.json
  .github/workflows/pages.yml    # builds + publishes to GitHub Pages
  justfile                       # just setup | dev | site | serve | rdf | tables
  README.md · .gitignore
  .claude/skills/                # the bundled agent skills
```

The `site` and `base` in `astro.config.mjs` are derived from `--base-iri`, so
the site works at a domain root **or** as a GitHub *project* page
(`https://user.github.io/repo/`).

## Then

```bash
cd my-kb
just setup     # npm install (once; commit package-lock.json)
just dev       # live-preview: concept pages + the /graph browser
```

Author concepts under `knowledge/` (see the two examples), listing each in
`knowledge/index.md`. Typed relations become edges in the graph browser and
"Knowledge graph" panels on the pages. The `lokf` toolkit recipes
(`just serve | rdf | tables`) run via `uvx`, so they only need `uv`.

## Publish

Push to GitHub and set **Settings → Pages → Source** to **GitHub Actions** —
the `pages` workflow builds the Astro site and deploys on every push to `main`.

## Idea → published site, with an agent

The scaffold ships the bundled agent skills, so you can open the new repo in
[Claude Code](https://claude.com/claude-code) and say *"build a knowledge base
of …"*. The `scaffold-knowledge-base` and `author-concept` skills drive the
whole path — scaffold, author, validate, publish.
