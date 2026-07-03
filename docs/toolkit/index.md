# Toolkit

The `lokf` Python package is the toolkit around the format: everything you
need to **load** a bundle, **inspect** the vocabulary, **project** markdown to
RDF, **propose** typed relations from prose links, and **export** the result
as a graph or as schema.org JSON-LD. The format itself stays where it belongs
— in `lokf.yaml` and the [specification](../specification.md); the toolkit
never hardcodes a type or predicate it can read from the schema.

| Module | What it gives you |
|---|---|
| `lokf.model` | `load_bundle()` → `Bundle` / `Concept` objects, JSON-LD and `rdflib.Graph` projection |
| `lokf.schema` | `vocabulary()` → the typed-relation slots and `RelationType` vocabulary, straight from `lokf.yaml` |
| `lokf.parse` | frontmatter parsing helpers (`parse_concept`, `isoify`) |
| `lokf.propose` | heuristic [relation proposer](proposer.md) + the `lokf propose` CLI |
| `lokf.export` | Cytoscape.js graph elements and schema.org `Dataset` JSON-LD |
| `lokf.build` | the `lokf-build` console script that regenerates every artifact |

## Install

!!! warning "Not on PyPI yet"

    `lokf` is not published to PyPI. Until it is, install straight from git —
    after release, this becomes a plain `uv add lokf`.

=== "uv"

    ```bash
    uv add "lokf @ git+https://github.com/nicholsn/lokf"
    ```

=== "pip"

    ```bash
    pip install git+https://github.com/nicholsn/lokf
    ```

    Note that pip bypasses `uv.lock` (the locked toolchain) — fine for
    consumers of the package; contributors should use `uv sync`.

Working inside a clone of this repository? `uv sync` already installs the
package in editable mode — see [Getting started](../getting-started.md).

## A five-minute tour

Everything below runs against the committed
[reference bundle](../examples.md), from the repository root:

```python
import lokf

# Load a bundle: a directory of markdown files, nothing else.
bundle = lokf.load_bundle("examples/acme-knowledge")
len(bundle.concepts)        # -> 6
bundle.base_iri             # -> 'https://acme.example/knowledge/'

# Concepts are addressable by Concept ID, path, or IRI.
wau = bundle.get("metrics/weekly-active-users")
wau.type, wau.title         # -> ('Metric', 'Weekly Active Users')
wau.data["formula"]         # frontmatter is a plain dict (body included)

# The same bundle, as RDF — this is the committed 86-triple projection.
g = bundle.graph()
len(g)                      # -> 86
print(g.serialize(format="turtle"))
```

And the vocabulary side — the typed-relation fields, read from the LinkML
schema rather than hardcoded:

```python
vocab = lokf.vocabulary()

sorted(vocab.relation_slots)
# -> ['about', 'definedBy', 'dependsOn', 'derivedFrom', 'hasPart', 'isPartOf',
#     'measures', 'references', 'relatedTo', 'sameAs', 'source']

vocab.relation_slots["derivedFrom"].curie   # -> 'prov:wasDerivedFrom'
vocab.relation_slots["measures"].domains    # -> frozenset({'Metric'})
vocab.expand("prov:wasDerivedFrom")         # -> 'http://www.w3.org/ns/prov#wasDerivedFrom'
```

!!! tip "The schema travels with the package"

    `vocabulary()` and `load_context()` resolve `lokf.yaml` and
    `lokf.context.jsonld` in this order: an explicit path argument first,
    then a checkout found by walking up from the current directory — so
    local schema edits always win — and only then the copies packaged
    inside the wheel, the fallback that lets an installed `lokf` work
    outside a repo checkout.

## Where next

<div class="grid cards" markdown>

-   :material-hammer-wrench:{ .lg .middle } **Build your own knowledge base**

    ---

    From an empty directory to a validated, queryable bundle — authoring,
    validation, proposals, RDF, and a graph view.

    [:octicons-arrow-right-24: Tutorial](tutorial.md)

-   :material-link-variant:{ .lg .middle } **Relation proposer**

    ---

    How `lokf propose` turns prose links into typed-relation suggestions,
    and where its heuristics stop.

    [:octicons-arrow-right-24: Proposer](proposer.md)

-   :material-graph:{ .lg .middle } **Knowledge graph**

    ---

    The reference bundle rendered as an interactive graph, built with
    `lokf.export`.

    [:octicons-arrow-right-24: Knowledge graph](../graph.md)

-   :material-api:{ .lg .middle } **Python reference**

    ---

    Generated API docs for every module in the package.

    [:octicons-arrow-right-24: API reference](../reference/api.md)

</div>
