---
title: Declarative navigation views
description: Configure static entry points, related-concept tables, families, and timelines for a LOKF knowledge base.
sidebar:
  label: Navigation views
---

Use `lokf.views.yaml` to give readers a starting point in your knowledge graph. A **view** names a task, such as “Explore metrics.” Its **roots** are the concepts a reader can start from. Each **section** follows typed relations from one root and shows the matching concepts together. The site builds these pages as static HTML and updates them when you rebuild with new content.

## Try the starter view

In a site created with `lokf new` from 0.11.0 or later, copy `lokf.views.example.yaml` to `lokf.views.yaml` beside `site.config.mjs` and run `npm run dev`. The example works with the two concepts supplied by the scaffold. Older sites can adopt the renderer and exporter from a fresh scaffold. [Scaffold a knowledge base](/toolkit/scaffold/#add-a-navigation-view) · [Upgrade an existing site](/toolkit/scaffold/#upgrade-an-existing-site)

```yaml
version: "1"
views:
  - id: metrics
    title: Explore metrics
    description: Choose a metric to see the concepts it measures.
    roots: {type: Metric}
    index: {layout: list, embed: [definitions]}
    sections:
      - id: definitions
        title: What this metric measures
        path:
          - {out: measures, type: GlossaryTerm}
        display: {layout: list}
```

Open **Explore metrics** on the home page. Under **Weekly Active Users**, the preview links to **Active User** because the metric records a `measures` relation to that glossary term. On the Active User page, **Appears in** takes you back to its row in the metric's section. The site keeps the authored introduction and concept directory alongside the configured views.

## Choose roots and paths

- Give each view an `id`, `title`, `description`, `roots` selector, and `index` display. Views appear on the home page in declaration order. View and section IDs start with a lowercase letter and use lowercase letters, digits, or hyphens. Section IDs are unique within a view.
- A view's sections appear on each root's concept page after its authored text. To show them under the concept's description instead, set `placement: before_text` on the view. Use it when the sections summarize the concept, such as a table of its stages, and its text is long.
- `roots.type` selects the exact class in the bundle's vocabulary. To start from a single overview, also set `roots.concept` to its bundle-relative concept ID, such as `guides/overview`, without the `.md` extension.
- A section supplies an `id`, `title`, `path`, and `display`. Its path contains one to four steps. Each step has exactly one direction, `out` or `in`, and can filter the reached concepts with an exact `type`. A predicate can be a projected relation name, a CURIE, or its full IRI.
- Each step reads local concept links from the same graph as `lokf export`, including typed entries under `relations`. An incoming step reads an existing assertion backwards. A section lists each matching endpoint once and omits its own root. A multi-step result includes a **How are these connected?** disclosure with one matching chain.

For a custom frontmatter key to appear as a graph edge, give the slot a `slot_uri`, a concept reference range, and `multivalued: true` on a concept class. Use `lokf vocab --bundle knowledge` to check which relation names your manifest can follow. Single-valued frontmatter references can participate in validation even when they produce no explorer edge.

For example, to answer “Which metrics use tables from this dataset?” in the Acme bundle, select `roots: {type: Dataset}` and add this section. Starting from **Events**, it finds **User Events**, then **Weekly Active Users**. The second step selects metrics even when other kinds of concept also derive from the same table. [Acme example bundle](/examples/)

```yaml
sections:
  - id: metrics
    title: Metrics using this dataset
    path:
      - {out: hasPart, type: Table}
      - {in: derivedFrom, type: Metric}
    display: {layout: list}
```

## Families and workflow stages

For a domain vocabulary with modalities, data stages, and scientific capabilities, a reader can choose a broad data family, see its stages in dependency order, and open the research capabilities each stage enables. This complete manifest shows how the vocabulary's relations drive the view.

```yaml
version: "1"
views:
  - id: modalities
    title: Follow curation for a data modality
    description: Choose a data family and follow its documented stages.
    roots: {type: Modality}
    placement: before_text
    index:
      layout: list
      family_by: {out: isPartOf}
    sections:
      - id: stages
        title: Documented data stages
        path: [{in: modality, type: DataStage}]
        display:
          layout: table
          order_by: {out: derivedFrom}
          columns:
            - {field: title, label: Data stage}
            - {relation: {out: processingLevel, type: ProcessingLevel}, label: Processing level}
            - {relation: {out: curationType, type: CurationType}, label: Curation type}
            - {relation: {out: unlocks, type: ScientificCapability}, label: Unlocks}
            - {field: formats, label: Formats}
            - {field: processing_step, label: How it is produced}
```

**Family navigation.** On a list index, `family_by` takes a single step from a selected concept to a parent. Each selected concept with no parent in the selection heads a family. Under it the site lists all direct and indirect descendants alphabetically. A concept can appear under several top-level families and appears just once in each. Its return link targets its first occurrence. A family heading opens the concept page, and a section link jumps to its first populated section.

**Stage ordering.** On a list or table section, `order_by` takes a single step from a row to its predecessors. In this example, curated tables derive from typed tables. That places typed tables first, even when both stages have the same processing level. The order applies to the complete set of rows before previews or pagination. Only predecessors within the section impose an order. When several rows are eligible, the compiler chooses by title, then IRI. Sections with at least two rows indicate whether the links establish a complete order, leave some choices open, or supply no ordering evidence. Cycles in the selected family or predecessor relations cause a build error.

**Relation-backed cells.** Here, the **Unlocks** cell starts from the stage in its own row. Each capability reached through `unlocks` appears as a link in that cell. To show the same relation in a table of capabilities, use `{label: Enabling stages, relation: {in: unlocks, type: DataStage}}`. Relations support the same directions and type filter as a path step. Each target appears once per cell, in title and IRI order. An empty cell reads **Not recorded**. An editorial description such as “internal” contributes a value only if it is modeled in the graph or supplied in a field column.

## Displays

The index and every section choose one layout.

| Layout | Configuration and behavior |
| --- | --- |
| `list` | Shows linked titles. The default order is ascending by title, then by IRI. |
| `table` | Requires an ordered `columns` list beginning with a labeled `field: title` column. Each column declares a label and exactly one source. `field` reads a top-level scalar or scalar list on the displayed record. `relation` follows a single step and links to the matching concept pages. |
| `timeline` | Requires a single-valued `date` or `datetime` field named in `date` and a visible `date_label`. The index or section groups rows by calendar day in the date's written offset. `direction` defaults to `desc` and can be `asc`. Ties sort by title and IRI. Missing and malformed dates appear under **Date not recorded**. |

For a publication, an edition can be a root and its developments a section. To group the developments under the day the edition **reported** them, configure the section as below. With `date_from: root`, the date belongs to the edition. Omit that option to read the date from each development.

```yaml
display:
  layout: timeline
  date_from: root
  date: issue_date
  date_label: Reported in this edition
```

A list or timeline index can use `embed` to preview named sections in the specified order. Each preview shows up to three rows with a link to the full section. A root with no rows in a section shows no preview of it. Titles fall back to the concept ID. Missing field values show **Not recorded**. The compiler checks fields against the effective vocabulary, including inherited slots. An untyped section may contain multiple classes, and a field present on only some of them uses the missing-value display for the others.

## Pages, links, and counts

| Where the reader lands | What they can do |
| --- | --- |
| Home | Open a view in manifest order, use **All concepts**, or continue to the authored introduction. |
| `/views/<view-id>/` | Choose a root. Indexes show 20 roots or 20 whole families per page. |
| A root's concept page | Read its authored text and then its sections in declaration order, or the sections first when the view sets `placement: before_text`. A section with no rows for that root is left off the page. Each section has its own fragment, such as `#view.metrics.definitions`, and shows up to 25 rows per page. |
| A section member's concept page | Follow **Appears in** to the row on the page that contains it. Concepts belonging to several sections have multiple return links. |

Continuation routes start at page two. An index uses `/views/<view-id>/page/<n>/`. A section uses `/views/<view-id>/sections/<section-id>/<concept-id>/page/<n>/`. Page links use the site's configured base and the concept's bundle-relative ID. A concept can have a different RDF IRI. Counts refer to distinct rows before pagination. Links inside a table cell leave row counts and section membership unchanged.

## Build and troubleshoot

`npm run build` detects `lokf.views.yaml`, compiles it alongside the graph, and writes the static site into `dist/`. During `npm run dev`, creating, changing, or removing the manifest triggers a fresh export. To inspect the compiler's `views.json` and diagnostics directly, run this from the KB root with the matching LOKF toolkit.

```sh
lokf export knowledge --out-dir build/views --views lokf.views.yaml
```

If a generated view URL coincides with an authored section guide, the build reports the conflicting path. Give the view or section a distinct URL.

The version 1 LinkML schema describes the keys and structures you can write. The compiler also checks the predicates, types, and fields against the vocabulary used for this export. An unknown predicate produces an error with its position in the manifest. For a valid path with no matching records, the diagnostics report the first step that produced an empty result and how many roots encountered it. [Views manifest schema (LinkML)](/schemas/lokf-views-v1.yaml) · [Domain vocabularies](/guide/domain-vocabularies/)

The manifest is site configuration. Its table and path design draws on SHACL UI's use of a focus node, inverse relations, and linked values in tables. LOKF uses the manifest to choose entry points and generate canonical links and static routes. [SHACL 1.2 UI, §12.2.10](https://www.w3.org/TR/2026/WD-shacl12-ui-20261111/)
