# Linked Open Knowledge Format

LOKF is a **semantic profile of Google's [Open Knowledge Format
(OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog)**. It keeps
OKF's markdown-plus-frontmatter authoring model but binds every concept, field,
and relationship to **schema.org, W3C DCAT, and W3C PROV-O**, so a bundle of
markdown files is *also* valid **JSON-LD** that expands losslessly to **RDF**.
The format is defined once in **LinkML**; the JSON-LD context, JSON Schema,
SHACL shapes, and OWL ontology are all generated from that single source.

> One sentence: *write OKF markdown, get a queryable knowledge graph for free.*

## Why

OKF v0.1 is deliberately minimal — the only required field is `type`, links are
untyped, and there's no shared vocabulary. LOKF adds exactly three things while
keeping OKF's ergonomics:

1. **Shared meaning** — types and fields map to public ontology terms.
2. **Typed relationships** — `dependsOn`, `derivedFrom`, `isPartOf`, … each
   pinned to an RDF predicate, instead of one untyped markdown link.
3. **A real graph** — the same bundle is queryable with SPARQL, validatable
   with SHACL, and reason-able with OWL.

It stays **bidirectionally compatible**: every LOKF bundle is a valid OKF
bundle, and every OKF bundle is valid LOKF with default mappings.

## A concept at a glance

Ordinary OKF markdown, where every key has a defined RDF meaning:

```markdown title="metrics/weekly-active-users.md"
---
type: Metric                                    # -> rdf:type lokf:Metric
id: https://acme.example/knowledge/metrics/weekly-active-users   # -> @id (subject)
title: Weekly Active Users                       # -> schema:name
unit: users                                      # -> schema:unitText
timestamp: 2026-06-30T12:00:00Z                  # -> schema:dateModified
derivedFrom: [ .../tables/user-events ]          # -> prov:wasDerivedFrom
dependsOn:   [ .../glossary/active-user ]        # -> dcterms:requires
measures:    [ .../glossary/active-user ]        # -> lokf:measures
---
# Definition
Distinct users with a qualifying event in a trailing 7-day window.
```

Attach the published [`lokf.context.jsonld`](reference/artifacts.md) and this
expands to RDF triples using `schema:`, `prov:`, `dcterms:`, and `lokf:`
predicates — no separate file.

## Explore

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Getting started**

    ---

    Install with `uv`, regenerate every artifact with one command, and
    validate your first bundle.

    [:octicons-arrow-right-24: Getting started](getting-started.md)

-   :material-file-document-outline:{ .lg .middle } **Guide**

    ---

    Bundles, concept anatomy, typed relationships, the type vocabulary, and
    how markdown becomes RDF.

    [:octicons-arrow-right-24: Bundles & concepts](guide/concepts.md)

-   :material-graph:{ .lg .middle } **Example bundle**

    ---

    Walk through the conformant six-concept `acme-knowledge` reference
    bundle and its RDF projection.

    [:octicons-arrow-right-24: Example bundle](examples.md)

-   :material-book-open-variant:{ .lg .middle } **Specification**

    ---

    The full LOKF v0.1 specification — motivation, conformance,
    versioning, and the complete field tables.

    [:octicons-arrow-right-24: Specification](specification.md)

</div>

## Status

!!! warning "Draft profile"

    LOKF v0.1 is a **draft profile** and is **not affiliated with or endorsed
    by Google**. "Open Knowledge Format" / "OKF" refer to the format published
    by Google Cloud
    ([`GoogleCloudPlatform/knowledge-catalog`](https://github.com/GoogleCloudPlatform/knowledge-catalog));
    LOKF extends it under its open terms.

## License

CC-BY-4.0 — see
[`LICENSE`](https://github.com/nicholsn/lokf/blob/main/LICENSE).
