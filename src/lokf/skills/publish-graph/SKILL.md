---
name: publish-graph
description: Serve a LOKF bundle locally with 'lokf serve' to get a SPARQL endpoint and a live graph explorer, and drive the /sparql endpoint programmatically from an agent. Use to publish or interactively explore a knowledge base.
---

# Publish a LOKF graph locally

## Purpose

`lokf serve <bundle>` starts a local HTTP server that exposes the bundle as a
live RDF graph: a SPARQL endpoint an agent can hit programmatically, plus a
browser graph explorer for humans. Use it to publish a bundle for interactive
exploration or to let another process query it over HTTP instead of shelling
out to `lokf query`.

## When to use

- You want a persistent endpoint to fire many queries at, not one-shot CLI runs.
- A human needs to see the concept graph rendered.
- Another agent/service needs to query the KB over HTTP.

## Start the server

```bash
lokf serve examples/acme-knowledge --host 127.0.0.1 --port 8000
```

Defaults are host `127.0.0.1`, port `8000`. The process runs in the foreground;
stop it with Ctrl-C. When testing programmatically, start it in the background
and poll the endpoint before querying.

## Routes

- `GET /` — the graph explorer (Cytoscape visualization of the concepts).
- `GET /sparql?query=<urlencoded>` — run a SPARQL query, get results back.
- `POST /sparql` — send the query in the request body (use for long queries).
- `GET /graph.json` — the graph as JSON for the viz; accepts an optional
  `?query=` CONSTRUCT to scope the rendered subgraph.
- `GET /static/cytoscape.min.js` — the bundled viz library.

The same preset schema prefixes apply as in `lokf query` (`lokf:`, `schema:`,
`prov:`, `dcterms:`, `rdfs:`, `owl:`, `xsd:`, …), so `/sparql` queries need no
PREFIX block.

## Hit /sparql programmatically

GET with the query URL-encoded, requesting SPARQL JSON results:

```bash
curl -sG http://127.0.0.1:8000/sparql \
  --data-urlencode 'query=SELECT ?s ?title WHERE { ?s a lokf:Metric ; dcterms:title ?title }' \
  -H 'Accept: application/sparql-results+json'
```

POST for larger queries (body is the SPARQL text):

```bash
curl -s http://127.0.0.1:8000/sparql \
  -H 'Content-Type: application/sparql-query' \
  --data 'SELECT (COUNT(?s) AS ?n) WHERE { ?s a ?t }'
```

Fetch a scoped subgraph for rendering:

```bash
curl -sG http://127.0.0.1:8000/graph.json \
  --data-urlencode 'query=CONSTRUCT { ?s ?p ?o } WHERE { ?s a lokf:Metric ; ?p ?o }'
```

From Python, an agent can `urllib.request`/`requests` the same URL and parse the
SPARQL-results JSON (`bindings` under `results`).

## Method

1. `lokf serve <bundle>` (background it for automated use).
2. Confirm it is up: a trivial `ASK { ?s ?p ?o }` against `/sparql` should
   return `true`.
3. Issue the real queries against `/sparql`; open `/` in a browser to inspect
   the graph visually.
4. Stop the server when done.

## Done when

- `/sparql` answers a known query with the expected rows, and `/` renders the
  bundle's concept graph.
