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

# Run the test suite
test:
    uv run --group dev pytest

# Serve the Astro docs site locally with live reload (web/)
docs:
    cd web && npm install && npm run dev

# Build the Astro docs site exactly as CI does (web/)
docs-build:
    cd web && npm ci && npm run build
