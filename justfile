# List available recipes
default:
    @just --list

# Regenerate every artifact from lokf.yaml, validate the reference bundle, emit RDF
build:
    uv run lokf-build

# Remove generated scratch files (committed artifacts like examples/*.nt are left alone)
clean:
    rm -f examples/*.bundle.json lokf.context.base.jsonld *.err

# Project a concept file or bundle directory to RDF (Turtle) on stdout
gen-rdf-turtle FILE:
    uv run lokf convert --format ttl {{FILE}}

# Run a SPARQL query over a bundle (schema prefixes are preset)
query BUNDLE SPARQL:
    uv run lokf query {{BUNDLE}} {{SPARQL}}

# Serve a bundle locally: SPARQL endpoint + live graph explorer
serve BUNDLE:
    uv run lokf serve {{BUNDLE}}

# Sync the vendored cytoscape.js: the package copy is canonical; the docs
# site copies from it (a test guards the two against drift).
sync-cytoscape:
    cp src/lokf/static/cytoscape.min.js docs/assets/js/cytoscape.min.js

# Run the test suite
test:
    uv run --group dev pytest

# Serve the docs locally with live reload
docs:
    uv run --group docs mkdocs serve

# Build the docs site with the locked toolchain (strict — the same check CI runs)
docs-build:
    uv run --locked --group docs mkdocs build --strict
