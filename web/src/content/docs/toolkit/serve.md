---
title: Serve
description: Publish a bundle locally as a SPARQL endpoint and live graph explorer with lokf serve.
sidebar:
  order: 4
---

`lokf serve` publishes a bundle locally as a **SPARQL endpoint** plus a **live
graph explorer** — the reference bundle you see on the [Knowledge
graph](/graph/) page, served from your own checkout.

```bash
uv run lokf serve examples/acme-knowledge
# lokf: 86 triples from examples/acme-knowledge
# lokf: SPARQL endpoint  http://127.0.0.1:8000/sparql
# lokf: graph explorer   http://127.0.0.1:8000/
# lokf: Ctrl-C to stop
```

It binds `127.0.0.1:8000` by default; `--host` and `--port` change that. The
`just serve` recipe wraps the command:

```bash
just serve examples/acme-knowledge
```

## Routes

| Route | Method | What it returns |
|---|---|---|
| `/sparql` | `GET ?query=` / `POST` | SPARQL 1.1 protocol — SELECT/ASK return `application/sparql-results+json`, CONSTRUCT/DESCRIBE return Turtle |
| `/graph.json` | `GET` (optional `?query=` CONSTRUCT) | cytoscape.js elements for the graph |
| `/` | `GET` | the interactive graph explorer (HTML) |
| `/static/cytoscape.min.js` | `GET` | the bundled viz library |

## Query it with curl

The endpoint speaks the standard SPARQL protocol, so any client works:

```bash
curl -s 'http://127.0.0.1:8000/sparql' \
  --data-urlencode 'query=SELECT ?s ?name WHERE { ?s schema:name ?name } ORDER BY ?name'
```

The schema prefixes are preset here exactly as they are for
[`lokf query`](/toolkit/query/), so your query needs no `PREFIX` block.

## Fully offline

The server ships everything it needs. The graph explorer's JavaScript
(`cytoscape.min.js`) is served from the package at `/static/`, nothing is
fetched from a CDN, and no telemetry leaves the machine. `lokf serve` runs
with no network access at all — handy for air-gapped review of a knowledge
base.
