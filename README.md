# Linked Open Knowledge Format (LOKF)

A **semantic profile of Google's Open Knowledge Format (OKF)**. LOKF keeps OKF's
markdown-plus-frontmatter authoring model but binds every concept, field, and
relationship to **schema.org, W3C DCAT, and W3C PROV-O**, so a bundle of markdown
files is *also* valid **JSON-LD** that expands losslessly to **RDF**. The format is
defined once in **LinkML**; the JSON-LD context, JSON Schema, SHACL shapes, and OWL
ontology are all generated from that single source.

> One sentence: *write OKF markdown, get a queryable knowledge graph for free.*

**Documentation:** <https://lokf.nolan-nichols.com/>

## Why

OKF v0.1 is deliberately minimal — the only required field is `type`, links are
untyped, and there's no shared vocabulary. LOKF adds exactly three things while
keeping OKF's ergonomics:

1. **Shared meaning** — types and fields map to public ontology terms.
2. **Typed relationships** — `dependsOn`, `derivedFrom`, `isPartOf`, … each pinned
   to an RDF predicate, instead of one untyped markdown link.
3. **A real graph** — the same bundle is queryable with SPARQL, validatable with
   SHACL, and reason-able with OWL.

It stays **bidirectionally compatible**: every LOKF bundle is a valid OKF bundle,
and every OKF bundle is valid LOKF with default mappings.

## Files

| Path | What it is | Hand-edited? |
|------|------------|:---:|
| `lokf.yaml` | **The LinkML schema — the single source of truth.** | ✅ edit this |
| `SPEC.md` | The human-readable specification. | ✅ |
| `lokf.context.jsonld` | Generated JSON-LD `@context` (+ `type`→`@type`, `id`→`@id` aliases). Attach to concepts to get Linked Data. | ⚙️ generated |
| `lokf.schema.json` | Generated JSON Schema — validates frontmatter / bundles. | ⚙️ generated |
| `lokf.shacl.ttl` | Generated SHACL shapes — validates the RDF graph. | ⚙️ generated |
| `lokf.owl.ttl` | Generated OWL ontology — reasoning & alignment. | ⚙️ generated |
| `lokf.sql` | Generated relational schema — `CREATE TABLE` DDL (FKs for typed relations). | ⚙️ generated |
| `src/lokf/datamodel.py` | Generated Python bindings — `from lokf.datamodel import Metric`. | ⚙️ generated |
| `examples/acme-knowledge/` | A conformant 6-concept reference bundle. | ✅ |
| `examples/*.nt` | RDF triples produced from the example frontmatter. | ⚙️ generated |

## Anatomy of a LOKF concept

`metrics/weekly-active-users.md` — ordinary OKF markdown; every key has a defined
RDF meaning:

<!-- --8<-- [start:concept-glance] -->
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
<!-- --8<-- [end:concept-glance] -->

Attach `lokf.context.jsonld` and this expands to RDF triples using
`schema:`, `prov:`, `dcterms:`, and `lokf:` predicates — no separate file.

## Regenerate the artifacts

Everything downstream of `lokf.yaml` is generated. One command reproduces every
artifact, re-assembles the reference bundle, re-validates it, and re-emits the RDF:

```bash
uv sync
just build      # == uv run lokf-build
```

Or run the individual generators by hand:

<!-- --8<-- [start:gen-commands] -->
```bash
# JSON-LD context (aliased type->@type, id->@id for authoring)
uv run gen-jsonld-context lokf.yaml > lokf.context.base.jsonld
uv run gen-json-schema     lokf.yaml > lokf.schema.json
uv run gen-shacl           lokf.yaml > lokf.shacl.ttl
uv run gen-owl             lokf.yaml > lokf.owl.ttl
```
<!-- --8<-- [end:gen-commands] -->

The published `lokf.context.jsonld` is the generated context with two standard
JSON-LD keyword aliases applied so unmodified OKF frontmatter is valid Linked Data:

```python
import json
c = json.load(open("lokf.context.base.jsonld"))
c["@context"]["type"] = "@type"   # OKF's required field designates the RDF class
c["@context"]["id"]   = "@id"     # the concept IRI is the RDF subject
json.dump(c, open("lokf.context.jsonld", "w"), indent=2)
```

## Validate a bundle

<!-- --8<-- [start:validate-bundle] -->
```bash
# `just build` assembles examples/acme-knowledge.bundle.json from the markdown, then:
uv run linkml-validate -s lokf.yaml -C KnowledgeBundle examples/acme-knowledge.bundle.json
# -> No issues found

# Or validate a single concept against its class
uv run linkml-validate -s lokf.yaml -C Metric metric.json
```
<!-- --8<-- [end:validate-bundle] -->

## Markdown → RDF in one command

The `lokf` CLI projects a concept — or a whole bundle directory — straight to
RDF. No context wiring, no glue code:

<!-- --8<-- [start:quickstart-rdf] -->
```bash
# a single concept -> Turtle on stdout
uv run lokf convert examples/acme-knowledge/metrics/weekly-active-users.md --format ttl

# the same thing behind the just recipe
just gen-rdf-turtle examples/acme-knowledge/metrics/weekly-active-users.md
```

`--format` also takes `nt`, `jsonld`, `xml`, `n3`, and `trig`; `--output FILE`
writes to disk instead of stdout. Point `convert` at the bundle directory
(`examples/acme-knowledge`) to project all six concepts at once.

Prefer to stay in Python? `lokf.rdf.serialize` is the same projection the CLI
calls:

```python
from lokf import rdf

# a concept file, or the bundle directory — either resolves IRIs correctly
print(rdf.serialize("examples/acme-knowledge/metrics/weekly-active-users.md", "ttl"))
```
<!-- --8<-- [end:quickstart-rdf] -->

This is the whole thesis: OKF authoring in, RDF knowledge graph out.

## Two projections: a graph *and* tables

Because LOKF is defined once in LinkML, a well-modeled bundle projects **two**
ways — the *literal* knowledge graph and the *abstract* one (well-modeled,
linked data you can put in tables):

- **A graph** — markdown → JSON-LD → RDF, queryable with SPARQL, validatable
  with SHACL, reason-able with OWL (shown above).
- **Tables** — the same schema generates typed **Python bindings**
  (`src/lokf/datamodel.py`) and a **relational schema** (`lokf.sql` — one table
  per type, foreign keys for the typed relations). So the same well-modeled data
  is either a queryable graph *or* a set of linked tables: DataFrames to analyze,
  SQL to persist, a lakehouse to scale.

```python
from lokf.datamodel import Metric

Metric(id="https://acme.example/knowledge/metrics/wau",
       type="Metric", title="Weekly Active Users", unit="users")
```

`lokf tables` projects a whole bundle to linked tables — one per type plus a
`relations` edge table (needs `lokf[tables]`):

```bash
lokf tables examples/acme-knowledge --format parquet  --output build/tables
lokf tables examples/acme-knowledge --format bigquery --location gs://bucket/lokf
```

## Start your own

`lokf new my-kb` scaffolds a complete knowledge-base repo — a starter bundle, a
full Astro site with concept pages and the interactive **graph browser**
(`/graph`, plus `graph.jsonld`), a GitHub Pages workflow, a `justfile`, and the
bundled agent skills — so you (or an AI agent) can go from an idea to a
published, queryable knowledge graph:

```bash
lokf new my-kb --title "My Knowledge Base"
cd my-kb && just setup && just dev
```

See the [scaffold docs](https://lokf.nolan-nichols.com/toolkit/scaffold/).

## Status

LOKF v0.1 is a **draft profile** and is **not affiliated with or endorsed by
Google**. "Open Knowledge Format" / "OKF" refer to the format published by Google
Cloud (`github.com/GoogleCloudPlatform/knowledge-catalog`); LOKF extends it under
its open terms.

## AI assistance

LOKF is developed openly and with substantial AI assistance (Claude) — including
the toolkit, the LinkML schema, the documentation, and this README. Nolan
Nichols reviews and takes full responsibility for everything committed. Per the
project's [AI Covenant](AI_COVENANT.md), AI is a tool, not a co-author: it is
never credited in commit messages, and every contribution is owned and defended
by a human. See [CONTRIBUTING.md](CONTRIBUTING.md) to get involved.

## License

CC-BY-4.0 — see [`LICENSE`](https://github.com/nicholsn/lokf/blob/main/LICENSE).
It's a spec + vocabulary; if you'd rather put the scripts under a code license,
swap in MIT or Apache-2.0.
