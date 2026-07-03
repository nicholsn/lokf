# Getting started

Everything downstream of `lokf.yaml` — the JSON-LD context, JSON Schema, SHACL
shapes, and OWL ontology — is generated. One command reproduces every artifact,
re-assembles the reference bundle, re-validates it, and re-emits the RDF.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package and project manager
- [just](https://just.systems/) — task runner (optional; every recipe is a
  one-line `uv run …` you can also type directly)

## Install

```bash
git clone https://github.com/nicholsn/lokf.git
cd lokf
uv sync
```

`uv sync` creates a virtual environment with LinkML, rdflib, and PyYAML pinned
by `uv.lock`, and installs the `lokf` package with its `lokf-build` console
script.

## Regenerate the artifacts

=== "just"

    ```bash
    just build
    ```

=== "uv"

    ```bash
    uv run lokf-build
    ```

The build:

1. runs the four LinkML generators against `lokf.yaml`,
2. publishes the authoring context (aliasing `type` → `@type` and `id` → `@id`),
3. assembles `examples/acme-knowledge/` into a single bundle document,
4. validates the bundle against the schema, and
5. projects it to RDF (`examples/*.nt`).

You can also run the individual generators by hand:

```bash
uv run gen-jsonld-context lokf.yaml > lokf.context.base.jsonld
uv run gen-json-schema     lokf.yaml > lokf.schema.json
uv run gen-shacl           lokf.yaml > lokf.shacl.ttl
uv run gen-owl             lokf.yaml > lokf.owl.ttl
```

## Validate a bundle

```bash
# `just build` assembles examples/acme-knowledge.bundle.json from the markdown, then:
uv run linkml-validate -s lokf.yaml -C KnowledgeBundle examples/acme-knowledge.bundle.json
# -> No issues found

# Or validate a single concept against its class
uv run linkml-validate -s lokf.yaml -C Metric metric.json
```

See [Validation](guide/validation.md) for the JSON Schema / SHACL split.

## Markdown → RDF in ~10 lines

```python
import json, yaml
from rdflib import Graph

# from the repository root
raw = open("examples/acme-knowledge/metrics/weekly-active-users.md").read()
_, fm, body = raw.split("---", 2)
doc = yaml.safe_load(fm)
doc["body"] = body.strip()
doc["@context"] = json.load(open("lokf.context.jsonld"))["@context"]

g = Graph().parse(data=json.dumps(doc, default=lambda d: d.isoformat()), format="json-ld")
print(g.serialize(format="turtle"))
```

This is the whole thesis: OKF authoring in, RDF knowledge graph out. The
mechanics are covered in [Markdown to RDF](guide/markdown-to-rdf.md).

## Work on the docs

=== "just"

    ```bash
    just docs        # live-reloading dev server
    just docs-build  # strict build, exactly as CI runs it
    ```

=== "uv"

    ```bash
    uv run --group docs mkdocs serve
    uv run --group docs mkdocs build --strict
    ```
