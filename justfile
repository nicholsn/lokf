# biolink-model release `just biolink` adapts; examples/biolink/upstream.sha256 pins the files
biolink_version := "4.4.4"
biolink_raw := "https://raw.githubusercontent.com/biolink/biolink-model/v" + biolink_version + "/src/biolink_model/schema"

# List available recipes
default:
    @just --list

# Regenerate every artifact from lokf.yaml, validate the reference bundle, emit RDF
build:
    uv run lokf-build

# Remove generated scratch files (committed artifacts like examples/*.nt are left alone)
clean:
    rm -f examples/*.bundle.json lokf.context.base.jsonld *.err
    rm -rf examples/biolink/upstream examples/biolink/biolink_lokf.yaml examples/biolink/lokf.yaml

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

# Fetch biolink-model at the pinned tag (never committed), adapt it for LOKF, validate and project examples/biolink
biolink:
    mkdir -p examples/biolink/upstream
    curl -fsSL -o examples/biolink/upstream/biolink_model.yaml {{biolink_raw}}/biolink_model.yaml
    curl -fsSL -o examples/biolink/upstream/attributes.yaml {{biolink_raw}}/attributes.yaml
    cd examples/biolink/upstream && sha256sum --check ../upstream.sha256
    cp lokf.yaml examples/biolink/lokf.yaml
    uv run lokf adapt examples/biolink/upstream/biolink_model.yaml -o examples/biolink/biolink_lokf.yaml --lokf lokf.yaml
    uv run lokf validate examples/biolink/knowledge --schema examples/biolink/biolink_lokf.yaml --check-refs
    uv run lokf convert examples/biolink/knowledge --schema examples/biolink/biolink_lokf.yaml --format ttl

# Serve the Astro docs site locally with live reload (web/)
docs:
    cd web && npm install && npm run dev

# Build the Astro docs site exactly as CI does (web/)
docs-build:
    cd web && npm ci && npm run build
