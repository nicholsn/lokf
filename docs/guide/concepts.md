# Bundles & concepts

LOKF keeps OKF's authoring model intact: a **knowledge bundle** is a directory
tree of markdown files, each file describing one **concept** with a small YAML
frontmatter block. Everything here is readable with `cat` and diffable in git.

## Bundle structure

Identical to OKF §3. `index.md` and `log.md` remain reserved; distribution as a
git repo is recommended. LOKF adds **optional keys to the bundle-root
`index.md` frontmatter** — the one place OKF already permits frontmatter in an
index:

```yaml title="index.md (bundle root)"
---
lokf_version: "0.1"          # LOKF version this bundle targets
okf_version: "0.1"           # OKF version it remains compatible with
base_iri: https://acme.example/knowledge/     # resolves Concept IDs to Concept IRIs
context: https://w3id.org/lokf/context.jsonld # the @context to attach to concepts
title: Acme Knowledge Bundle
description: Canonical, agent-readable knowledge for Acme's data org.
license: https://creativecommons.org/licenses/by/4.0/
publisher:
  type: Organization
  id: https://acme.example
  name: Acme Corp
---
```

!!! note "Plain OKF consumers are unaffected"

    A consumer that ignores these keys sees a perfectly ordinary OKF bundle. A
    semantic consumer uses `base_iri` + `context` to lift the whole bundle
    into RDF.

## Concept documents

Every concept is a UTF-8 markdown file: a YAML **frontmatter** block followed
by a markdown **body**, exactly as in OKF. LOKF specifies what the frontmatter
keys *mean* by mapping each to an RDF property.

### Core frontmatter fields

`type` is the only required field (as in OKF). All others are optional.

| Field         | OKF | RDF property (`slot_uri`)          | Range   | Notes                                             |
|---------------|:---:|------------------------------------|---------|---------------------------------------------------|
| `type`        |  ✅ | `rdf:type` (via `@type`)           | class   | **Required.** Names a LOKF class.                 |
| `id`          |     | `@id` (subject)                    | IRI     | Concept IRI. Defaults to `base_iri` + Concept ID. |
| `title`       |  ✅ | `schema:name`                      | string  | close: `dcterms:title`, `rdfs:label`              |
| `description` |  ✅ | `schema:description`               | string  | close: `dcterms:description`                      |
| `resource`    |  ✅ | `schema:url`                       | IRI     | The underlying asset. close: `dcat:landingPage`, `prov:specializationOf` |
| `tags`        |  ✅ | `schema:keywords`                  | string* | close: `dcat:keyword`                             |
| `timestamp`   |  ✅ | `schema:dateModified`              | dateTime| exact: `dcterms:modified`                         |
| `created`     |     | `schema:dateCreated`               | dateTime| exact: `dcterms:created`                          |
| `version`     |     | `schema:version`                   | string  |                                                   |
| `license`     |     | `schema:license`                   | IRI     |                                                   |
| `author`      |     | `schema:author`                    | Agent*  | close: `dcterms:creator`, `prov:wasAttributedTo`  |
| `body`        |  ✅ | `schema:text`                      | string  | The markdown after the frontmatter.               |
| `citations`   |     | `schema:citation`                  | Citation*|                                                  |

(`*` = multivalued.)

!!! tip "Permissive by design"

    Producers MAY add any other keys; consumers MUST preserve unknown keys and
    MUST NOT reject documents that carry them (OKF §4.1). Missing optional
    fields, unknown `type` values, and broken cross-links MUST NOT cause
    rejection either.

### Body

Unchanged from OKF §4.2. Standard markdown, structural headings preferred. The
conventional headings `# Schema`, `# Examples`, and `# Citations` retain their
OKF meaning. The body is mapped to `schema:text` in the RDF projection.

## Next

- Give links meaning with [typed relationships](relationships.md).
- Pick the right class from the [type vocabulary](types.md).
