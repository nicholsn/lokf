# List available recipes
default:
    @just --list

# Regenerate every artifact from lokf.yaml, validate the reference bundle, emit RDF
build:
    uv run lokf-build

# Remove generated scratch files
clean:
    rm -f examples/*.bundle.json examples/*.nt lokf.context.base.jsonld *.err

# Serve the docs locally with live reload
docs:
    uv run --group docs mkdocs serve

# Build the docs site exactly as CI does (strict mode)
docs-build:
    uv run --group docs mkdocs build --strict
