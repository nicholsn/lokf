# List available recipes
default:
    @just --list

# Regenerate every artifact from lokf.yaml, validate the reference bundle, emit RDF
build:
    uv run lokf-build

# Remove generated scratch files (committed artifacts like examples/*.nt are left alone)
clean:
    rm -f examples/*.bundle.json lokf.context.base.jsonld *.err

# Run the test suite
test:
    uv run --group dev pytest

# Serve the docs locally with live reload
docs:
    uv run --group docs mkdocs serve

# Build the docs site with the locked toolchain (strict — the same check CI runs)
docs-build:
    uv run --locked --group docs mkdocs build --strict
