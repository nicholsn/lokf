# biolink-model as a LOKF domain

[Biolink-model](https://github.com/biolink/biolink-model) is the best-known
LinkML schema. This example makes its classes LOKF concepts: `type: Gene`
validates, projects as `a biolink:Gene`, and sits in one graph with a stock
LOKF `Dataset`.

```bash
just biolink
```

That fetches biolink-model at the pinned tag into `upstream/` and checks it
against `upstream.sha256`, copies `lokf.yaml` beside it, writes
`biolink_lokf.yaml` with `lokf adapt`, then validates and projects
`knowledge/` through `genomics.yaml`. The three generated files are ignored
by git; only the domain schema, the bundle and the checksums are committed.

`genomics.yaml` declares nothing of its own: importing the adapted copy is
enough. What `lokf adapt` changed, and why, is in the toolkit page for the
command and the *Domain schemas* guide on the documentation site.

Biolink-model is published under CC0 1.0 by the Biolink Model consortium; it
is fetched here, never vendored.
