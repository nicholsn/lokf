# Linked Open Knowledge Format (LOKF) — v0.1

A **semantic profile of Google's Open Knowledge Format (OKF)**. LOKF keeps OKF's
markdown-plus-frontmatter authoring model but binds every concept, field, and
relationship to **schema.org, W3C DCAT, and W3C PROV-O**, so a bundle of markdown
files is *also* valid **JSON-LD** that expands losslessly to **RDF**. The format is
defined once in **LinkML**; the JSON-LD context, JSON Schema, SHACL shapes, and OWL
ontology are all generated from that single source.

> One sentence: *write OKF markdown, get a queryable knowledge graph for free.*

**Documentation:** <https://www.nolan-nichols.com/lokf/>

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
| `examples/acme-knowledge/` | A conformant 6-concept reference bundle. | ✅ |
| `examples/*.nt` | RDF triples produced from the example frontmatter. | ⚙️ generated |

## Anatomy of a LOKF concept

`metrics/weekly-active-users.md` — ordinary OKF markdown; every key has a defined
RDF meaning:

```markdown
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

```bash
# JSON-LD context (then alias type->@type, id->@id for authoring — see below)
uv run gen-jsonld-context lokf.yaml > lokf.context.base.jsonld
uv run gen-json-schema     lokf.yaml > lokf.schema.json
uv run gen-shacl           lokf.yaml > lokf.shacl.ttl
uv run gen-owl             lokf.yaml > lokf.owl.ttl
```

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

```bash
# `just build` assembles examples/acme-knowledge.bundle.json from the markdown, then:
uv run linkml-validate -s lokf.yaml -C KnowledgeBundle examples/acme-knowledge.bundle.json
# -> No issues found

# Or validate a single concept against its class
uv run linkml-validate -s lokf.yaml -C Metric metric.json
```

## Markdown → RDF in ~10 lines

```python
import json, yaml
from rdflib import Graph

raw = open("metrics/weekly-active-users.md").read()
_, fm, body = raw.split("---", 2)
doc = yaml.safe_load(fm)
doc["body"] = body.strip()
doc["@context"] = json.load(open("lokf.context.jsonld"))["@context"]

g = Graph().parse(data=json.dumps(doc), format="json-ld")
print(g.serialize(format="turtle"))
```

This is the whole thesis: OKF authoring in, RDF knowledge graph out.

## Status

LOKF v0.1 is a **draft profile** and is **not affiliated with or endorsed by
Google**. "Open Knowledge Format" / "OKF" refer to the format published by Google
Cloud (`github.com/GoogleCloudPlatform/knowledge-catalog`); LOKF extends it under
its open terms.

## License

CC-BY-4.0 — see [`LICENSE`](LICENSE). It's a spec + vocabulary; if you'd rather put
the scripts under a code license, swap in MIT or Apache-2.0.
