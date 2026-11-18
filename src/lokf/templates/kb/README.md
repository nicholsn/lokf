# __KB_TITLE__

A [LOKF](https://lokf.nolan-nichols.com) knowledge base. Every markdown file in
`knowledge/` is one concept; together they are a queryable knowledge graph
*and* this website — an [Astro](https://astro.build) site with concept pages,
full-text search, and an interactive graph browser.

## Author

Add concept files under `knowledge/` (see the two examples). Each has YAML
frontmatter (a `type` and fields) plus a markdown body. The authored
`knowledge/index.md` is the site's home-page guide, followed by browsable
concept cards. Typed relations declared by LOKF or your domain schema become
edges in the graph and named connections on concept pages. Prose hyperlinks
remain ordinary links. Raw HTML in knowledge Markdown is escaped, and unsafe
link schemes are shown as text.

Search covers titles, descriptions, tags, body text, and optional claim/thesis
fields. The `/search` page offers type, tag, genre, status, trust, freshness,
and date filters when the data supports them. Its URL can be bookmarked.

The `/graph` page offers bounded neighborhoods for large bundles, a list view,
several layouts, typed incoming/outgoing connections, and path finding. Share
its URL to restore a view. The complete toolkit graph remains at `/graph.json`
and its JSON-LD projection at `/graph.jsonld`. A timeline of dated concepts
is off by default, since its default dates record when concepts were written.
To show it, choose date and relation fields in `src/temporal.config.mjs` and
set `enabled: true`.

Prefer an AI agent? The bundled skills in `.claude/skills/` drive the whole
workflow — open this repo in [Claude Code](https://claude.com/claude-code) and
ask it to build out the knowledge base from your idea.

## Work with it

Needs **Node 24** (or Node 22.23.4 or newer) and
[`uv`](https://docs.astral.sh/uv/). The site build runs the pinned LOKF toolkit
to export its graph and JSON-LD before Astro renders pages. The Pages workflow
installs both tools.

```bash
just setup    # npm install (once; commit package-lock.json)
just dev      # live-preview the site + graph browser
just site     # build the static site into dist/

just serve    # SPARQL endpoint + graph explorer (lokf toolkit, via uvx)
just rdf      # project the bundle to RDF / Turtle
just validate # check the bundle against the LOKF schema
just tables   # project the bundle to linked tables (CSV)
```

The `lokf` recipes use `uvx`, so no `pip install` is needed. For a local toolkit
checkout, set `LOKF_EXPORT_EXECUTABLE` to its `lokf` executable when building
the site. Set `LOKF_TOOLKIT_SPEC` to override the pinned package spec. The
default includes the `build` extra, whose LinkML reads a domain vocabulary
declared in `pyproject.toml`.

To offer a correction link on concept pages, set `repositoryUrl` to your GitHub
repository in `site.config.mjs`. For another host, set `correctionUrl` to its
correction form. The pages show recorded sources and review signals with their
trust tier; those signals do not prove a concept's claims.

## Publish to GitHub Pages

1. Point the repo at the URL you will publish at. `lokf new --base-iri
   https://you.example/my-kb/` does this for you, so if you scaffolded without
   the flag the simplest fix is to re-scaffold with it. Set by hand, it lives in
   four files:

   - `knowledge/index.md` — `base_iri`
   - `astro.config.mjs` — `site`, `base`, and the `base` passed to `remarkLokfLinks`
   - `src/lib/lokf.ts` — `BASE_IRI`
   - `knowledge/metrics/weekly-active-users.md` — the `measures:` cross-reference

   Missing one is silent: a concept carrying an absolute `id` never reaches the
   `BASE_IRI` fallback, so the graph looks right until a concept without one —
   or a bundle-relative reference — mints an IRI that does not match the rest.
2. Push to GitHub; in **Settings → Pages**, set the source to **GitHub Actions**.
3. The `pages` workflow builds the site and publishes it on every push to `main`.

## Responsible AI use

This knowledge base may be authored with AI assistance. You own everything you
commit — understand it, verify it, and don't credit an AI as a co-author. See
the [LOKF AI Covenant](https://github.com/nicholsn/lokf/blob/main/AI_COVENANT.md).
