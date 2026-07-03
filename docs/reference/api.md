# Python reference

The `lokf` package is the LOKF toolkit: the bundle model (`lokf.model`), the
schema vocabulary (`lokf.schema`), the parsing helpers (`lokf.parse`), the
[relation proposer](../toolkit/proposer.md) (`lokf.propose`), the graph and
JSON-LD exporters (`lokf.export`), and the `lokf-build` console script that
regenerates every artifact from `lokf.yaml` (`lokf.build`). For a guided
walkthrough, start with the [Toolkit overview](../toolkit/index.md).

::: lokf.parse

::: lokf.build

The bundle model — `load_bundle()` and the `Bundle`/`Concept` objects it
returns, including the JSON-LD and `rdflib.Graph` projections.

::: lokf.model

The vocabulary — typed-relation slots, the `RelationType` enum, and
CURIE/IRI helpers, all read from the LinkML schema rather than hardcoded.

::: lokf.schema

The relation proposer — turns prose links into typed-relation proposals and
applies accepted ones back into frontmatter (the `lokf propose` CLI).

::: lokf.propose

The exporters — Cytoscape.js graph elements and schema.org `Dataset` JSON-LD
for dataset-search markup.

::: lokf.export
