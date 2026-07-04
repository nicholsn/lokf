# __KB_TITLE__

A [LOKF](https://lokf.nolan-nichols.com) knowledge base. Every markdown file in
`knowledge/` is one concept; together they are a queryable knowledge graph
*and* this website — an [Astro](https://astro.build) site with concept pages
and an interactive **graph browser** at `/graph`.

## Author

Add concept files under `knowledge/` (see the two examples). Each has YAML
frontmatter (a `type` and fields) plus a markdown body; list new concepts in
`knowledge/index.md`. Typed relations between concepts (`measures`,
`dependsOn`, `isPartOf`, …) become edges in the graph and "Knowledge graph"
panels on the pages.

Prefer an AI agent? The bundled skills in `.claude/skills/` drive the whole
workflow — open this repo in [Claude Code](https://claude.com/claude-code) and
ask it to build out the knowledge base from your idea.

## Work with it

```bash
just setup    # npm install (once; commit package-lock.json)
just dev      # live-preview the site + graph browser
just site     # build the static site into dist/

just serve    # SPARQL endpoint + graph explorer (lokf toolkit, via uvx)
just rdf      # project the bundle to RDF / Turtle
just tables   # project the bundle to linked tables (CSV)
```

The `lokf` recipes use [`uvx`](https://docs.astral.sh/uv/), so they only need
`uv` installed — no `pip install`.

## Publish to GitHub Pages

1. Set `base_iri` in `knowledge/index.md` — and `site`/`base` in
   `astro.config.mjs` — to the URL you will publish at (already done if you
   passed `--base-iri` to `lokf new`).
2. Push to GitHub; in **Settings → Pages**, set the source to **GitHub Actions**.
3. The `pages` workflow builds the site and publishes it on every push to `main`.

## Responsible AI use

This knowledge base may be authored with AI assistance. You own everything you
commit — understand it, verify it, and don't credit an AI as a co-author. See
the [LOKF AI Covenant](https://github.com/nicholsn/lokf/blob/main/AI_COVENANT.md).
