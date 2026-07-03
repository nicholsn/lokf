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

--8<-- "README.md:gen-commands"

## Validate a bundle

--8<-- "README.md:validate-bundle"

See [Validation](guide/validation.md) for the JSON Schema / SHACL split.

## Markdown → RDF in one command

The `lokf convert` command projects a concept — or the whole bundle — to RDF
directly from the checkout you just cloned:

--8<-- "README.md:quickstart-rdf"

This is the whole thesis: OKF authoring in, RDF knowledge graph out. The
[Convert](toolkit/convert.md) page covers every format and flag, and the
mechanics of the projection are in [Markdown to RDF](guide/markdown-to-rdf.md).

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
