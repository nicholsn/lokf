# __KB_TITLE__

A [LOKF](https://lokf.nolan-nichols.com) knowledge base. Each concept file in
`knowledge/` contributes one record to the queryable graph and one page to the
[Astro](https://astro.build) site. Readers can search the concepts, explore
their connections on the **Graph** tab, or look up their types on the **Schema** tab.

## Author

Add concept files under `knowledge/` (see the two examples). Each has YAML
frontmatter (a `type` and fields) plus a markdown body. The authored
`knowledge/index.md` is the site's home-page guide, followed by browsable
concept cards. An `index.md` in a subdirectory becomes that section's page,
and a link to it goes there. Typed relations declared by LOKF or your domain
schema become edges in the graph and named connections on concept pages.
Prose hyperlinks remain ordinary links. Raw HTML in knowledge Markdown is
escaped, and unsafe link schemes are shown as text.

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

### Choose how readers enter the knowledge base

Copy `lokf.views.example.yaml` to `lokf.views.yaml` in the project root and
build the site. The starter adds **Explore metrics** to the home page,
previews definitions under each metric, and links each definition back to
its row. Edit the root type, relation path, and display for your vocabulary.
The dev server watches the manifest. Each build renders the configured
views as static HTML. A family index can group related concepts, and
table rows can follow predecessor links or display related concepts in
their own cells. [Declarative views reference](https://lokf.nolan-nichols.com/reference/declarative-views/)

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
just validate # check the bundle against its schema
just tables   # project the bundle to linked tables (CSV)
```

The `lokf` recipes use `uvx`, so no `pip install` is needed. For a local toolkit
checkout, set `LOKF_EXPORT_EXECUTABLE` to its `lokf` executable when building
the site. The site exporter and the `serve`, `rdf`, and `validate` recipes
use `lokf[build]==__LOKF_PACKAGE_VERSION__` by default. Set `LOKF_TOOLKIT_SPEC`
to use a different build-enabled package for those commands. The `tables`
recipe uses the matching release with the `tables` extra.

If you created this project **from a LOKF source revision between releases**,
use the same revision for local and Pages builds. With a local checkout,
run `uv sync --extra build` there before pointing the site at its executable.
For a portable build, set
`LOKF_TOOLKIT_SPEC` to `lokf[build] @ git+https://github.com/nicholsn/lokf.git@COMMIT`,
replacing `COMMIT` with the full commit that generated the scaffold.

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

## Schema browser

New sites enable `schemaBrowser: true` in `site.config.mjs`, adding a **Schema** tab at `/schema`.
The build exports the configured LinkML schema, including imported and abstract
classes, even when no records use them. The browser documents LOKF by default.
To use your own vocabulary, add its path to the project's `pyproject.toml`.

```toml
[tool.lokf]
schema = "schema/my-domain.yaml"
```

The path is relative to that file. To inspect the same vocabulary in the CLI,
run `lokf vocab --bundle knowledge --all`. In an MCP client, call
`get_vocabulary` with `{"bundle": "knowledge", "all": true}` when the server
runs from this project's root, or pass the absolute bundle path.

The overview has searchable class, slot, enumeration and datatype indexes.
Class pages show inheritance, mixins and effective slot ranges and constraints,
including class-specific overrides. The Cytoscape diagram starts with domain
classes, limits each view to 70 types, and lets readers focus on a class and its
neighbors. Dashed edges show inheritance; labeled edges show class-valued slots.
The linked reference tables also work without JavaScript.

Set `schemaBrowser: false` to omit the tab and its routes. Enabling it reserves
`schema/`; the build fails if a concept or view would collide with that path.
For an existing site, copy the schema pages, component, helpers, export script
and navigation integration from the current template. The exporter must support
`lokf export --schema-docs`, which adds a separate `schema.json` artifact without
changing the instance graph or the four-file registry producer contract.
