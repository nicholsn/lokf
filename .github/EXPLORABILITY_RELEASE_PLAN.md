# Next toolkit release: knowledge-base exploration

This is the implementation plan for the next `lokf` package release. The
format version stays at LOKF v0.2: search, layouts, and browsing are site and
toolkit capabilities, not new authoring syntax. Each item below has a tracked
GitHub issue.

## Release order

| ID | Priority | Issue | Depends on |
| --- | --- | --- | --- |
| E1 | P0 | [Make the scaffold consume the toolkit's vocabulary-aware graph and JSON-LD export](https://github.com/nicholsn/lokf/issues/193) | — |
| E2 | P0 | [Add default static full-text search to generated sites](https://github.com/nicholsn/lokf/issues/194) | E1 for trust facets |
| E3 | P0 | [Make large graphs navigable with bounded scopes, pagination, list view, and shareable state](https://github.com/nicholsn/lokf/issues/195) | E1 |
| E4 | P1 | [Add complementary layouts, relation-aware inspection, and a typed path finder](https://github.com/nicholsn/lokf/issues/196) | E3 |
| E5 | P1 | [Publish the authored index and improve concept browse, backlinks, and trust context](https://github.com/nicholsn/lokf/issues/197) | E1, E2 |
| E6 | P1 | [Make LOKF's own docs use the same graph explorer and document the new template](https://github.com/nicholsn/lokf/issues/198) | E3–E5 |
| E7 | P2 | [Add a generic, data-driven temporal evidence view when a bundle has suitable dates and relations](https://github.com/nicholsn/lokf/issues/199) | E1, E3 |
| E8 | Release gate | [Test a fresh scaffold, domain vocabulary, docs site, accessibility, and large-bundle performance](https://github.com/nicholsn/lokf/issues/200) | E1–E7 |

## Issue specifications

### E1 — One authoritative site projection

Run `lokf export` during generated-site builds. Serve its `graph.json` and
`concepts.jsonld` through the site, adding site URLs without reinterpreting
relations in TypeScript. Preserve domain-vocabulary classes/slots, CURIE
targets, reified-relation flags, and trust/status/staleness. A domain relation
such as the repository's `taughtBy: [kb:real]` fixture must appear in the
generated graph and JSON-LD. Keep the complete graph downloadable.

### E2 — Search every concept by default

Add header search and a dedicated result page over title, description, tags,
Markdown body, and optional claim/thesis fields. Rank useful fields, show
snippets, support multiword and prefix queries, and expose type, tag, genre,
status, trust, and date facets when data exists. Search/filter state survives
reload and browser Back through the URL. Results open the concept page or its
graph neighborhood. The static site must work on GitHub Pages without a
server and report index-load failures accessibly.

### E3 — Bounded graph navigation

Keep a whole-graph export and show a whole-graph canvas for small bundles.
For larger bundles, start from a concept or meaningful entry point, page
through neighbors, cap rendered nodes, and report omitted context. A list view
must offer keyboard access to the same nodes and connections. Filters, search,
scope, page, and selected node are restorable via the URL; graph links from
concept pages must focus the intended node.

### E4 — Graph questions and layouts

Offer connected-neighborhood, inferred-community, concept-type, spread, and
visible-hub layouts. Recompute the visible subgraph after filters change, allow
rearranging, and offer an edge-label toggle. Explain that community groups and
hub counts describe the current visible graph. Show a selected node's incoming
and outgoing typed connections and links to pages. Add a path finder between
two concepts that reports each predicate and direction; it may say no path
under current filters. Keep ordinary Markdown links distinct from asserted
graph edges.

### E5 — Better reading paths and trust

Render the bundle's root `knowledge/index.md` editorial content on the site
home, followed by browse cards. Make type and tag badges into browse links.
Group backlinks by their actual relation. Show available source, generation,
verification, status, trust tier, and staleness on pages without implying that
attribution proves a claim. Offer a reusable citation/permalink control and a
configurable correction link when the author supplies a repository URL.

### E6 — Use the template in LOKF's docs

Keep Starlight's documentation and search. Use the same reusable graph
explorer implementation as generated sites for the docs' example graph, rather
than maintaining a smaller fork. Update the scaffold guide, graph guide,
README, and release notes with setup requirements, search, graph states,
layouts, schema support, trust displays, and limitations. Verify the published
docs build and example graph behavior.

### E7 — Conditional temporal exploration

Provide a general timeline/evidence view only when the bundle supplies a date
field and a relation suitable for grouping records. Make date semantics and
relationship roles configurable; never assume newsletter-only classes such as
`Issue`, `Theme`, or `Development`. Every aggregate must link back to its
underlying concepts and label its counting method.

### E8 — Release verification

Build and inspect a freshly generated site at a root domain and a project
subpath. Include a domain-vocabulary fixture and a larger fixture. Run Python
tests, template JavaScript tests, the generated Astro build, and the docs
build. Check that search and graph controls are keyboard usable, URLs restore
views, static assets load under a subpath, and full-graph and JSON-LD exports
match the toolkit. Document measured build and browser payload costs for the
larger fixture. Bump the package version only with the release candidate and
keep the format version unchanged.

#### Local large-bundle measurement (2026-11-17)

A fresh scaffold with 1,000 synthetic `Document` concepts plus its two starter
concepts had 1,200 typed edges (a chain and 200 links to one hub). With the
checkout's local exporter and Node 25.6.0 on macOS, `npm run build` took
**3.36 seconds** after dependencies were installed. The output had 1,005 HTML
pages and 1,005 bounded graph-scope JSON files, 2,018 files and **51.6 MB**
raw in total. Scopes accounted for **36.3 MB**; the largest was 168 KB raw
(6.7 KB gzip), and no scope exceeded 180 nodes.

The complete `graph.json` was 710 KB raw / **28.6 KB gzip**;
`search-index.json` was 599 KB / **36.3 KB gzip**; the graph explorer's
JavaScript was 585 KB / **177 KB gzip**. The browser fetches an index and one
bounded scope for a large graph, while the complete export remains available.
Per-concept scopes duplicate data in the static output, so repository and
deployment size remain a scaling cost despite bounded browser views. These
figures are one local fixture, not a cross-platform performance guarantee.
