---
title: Scaffold a knowledge base (lokf new)
description: Create a new, publishable LOKF knowledge base — bundle, Astro site with the graph browser, and agent skills — with one command.
---

`lokf new <name>` scaffolds a complete, publishable knowledge base — in the
spirit of linkml-cookiecutter. One command, and you (or an AI agent) can go from
an idea to a queryable knowledge graph and a static website with **full-text
search** and an **interactive graph explorer**.

## Command

```bash
lokf new my-kb --title "My Knowledge Base" --base-iri https://myorg.github.io/my-kb/
```

Creates `my-kb/`:

```
my-kb/
  knowledge/                     # the LOKF bundle (index.md + example concepts)
  src/                           # the Astro site
    pages/index.astro            #   home: authored introduction and concept browsing
    pages/[...slug].astro        #   one page per concept, with relations panels
    pages/[...section].astro     #   one page per section index.md
    pages/search.astro           #   sitewide full-text search
    pages/search-index.json.ts   #   build-time search index
    pages/graph.astro            #   the interactive graph explorer
    pages/graph.json.ts          #   complete graph export
    pages/graph-index.json.ts    #   concept list for choosing a neighborhood
    pages/graph-data/            #   bounded concept-neighborhood views
    pages/graph.jsonld.ts        #   the whole bundle as JSON-LD (the RDF view)
    pages/temporal/              #   evidence timeline, off until enabled
    temporal.config.mjs          #   candidate date and relation fields
  scripts/export-graph.mjs       # uses the matching LOKF toolkit at build time
  site.config.mjs                # optional repository/correction link
  package.json · astro.config.mjs · tsconfig.json
  .github/workflows/pages.yml    # builds + publishes to GitHub Pages
  justfile                       # just setup | dev | site | serve | rdf | tables
  README.md · .gitignore
  .claude/skills/                # the bundled agent skills
```

The `site` and `base` in `astro.config.mjs` are derived from `--base-iri`, so
the site works at a domain root **or** as a GitHub *project* page
(`https://user.github.io/repo/`).

Building the site requires Node 24 (or Node 22.23.4 or newer) and `uv`.
The build runs the matching `lokf` package to produce the graph and JSON-LD,
so domain vocabulary relations and trust signals use the toolkit projection.
It installs the package with its `build` extra, because reading a domain
vocabulary declared in `pyproject.toml` needs LinkML.

## Then

```bash
cd my-kb
just setup     # npm install (once; commit package-lock.json)
just dev       # live-preview: concept pages, /search, and /graph
```

Author concepts under `knowledge/` (see the two examples). The authored
`knowledge/index.md` appears on the home page before concept cards. The site
search indexes concept titles, descriptions,
tags, and Markdown bodies, along with present claim or thesis fields. Search
results link to the concept page and its graph neighborhood. Readers can filter
by type, tag, status, genre, trust, freshness, or date, and sort by relevance
or newest content. The index is generated at build time and needs no search
service.

Typed relations become edges in the graph explorer and "Knowledge graph" panels
on the pages. The `lokf` toolkit recipes
(`just serve | rdf | tables`) run via `uvx`, so they only need `uv`.

## Explore

The graph opens on a concept neighborhood when a bundle is large enough to
make a whole-graph layout unwieldy. Its graph and list views share the same
typed relations. Choose a connected, community, type group, spread, or hub
layout; filter node and relation types; inspect connections; and copy a URL
that restores the view. The path finder shows a shortest chain through the
current filtered view, with an option to follow relation direction. Community
groups are inferred from the displayed relationships, and hub counts describe
the current view rather than global importance. The complete `graph.json` and
`graph.jsonld` exports remain
available for other tools.

A generic timeline of dated concepts is available but off by default: its
default dates record when concepts were created or written, which says little
about what they describe. To show it, choose date fields and a grouping
relation that mean something in your bundle in `src/temporal.config.mjs`, and
set `enabled: true`.

Each `index.md` below the bundle root becomes its section's page, at the
directory's address. A Markdown link to a section's `index.md` goes to that
page, and a link to the root `index.md` goes to the home page.
Concept pages show recorded sources and review signals, with permalink and
citation controls. Set `repositoryUrl` in `site.config.mjs` to offer a GitHub
correction link. Raw HTML in knowledge Markdown is escaped by default.

Search and layout are website features. They do not change the LOKF format or
turn ordinary Markdown links into asserted RDF relationships.

## Publish

Push to GitHub and set **Settings → Pages → Source** to **GitHub Actions** —
the `pages` workflow builds the Astro site and deploys on every push to `main`.

## Idea → published site, with an agent

The scaffold ships the bundled agent skills, so you can open the new repo in
[Claude Code](https://claude.com/claude-code) and say *"build a knowledge base
of …"*. The `scaffold-knowledge-base` and `author-concept` skills drive the
whole path — scaffold, author, validate, publish.
