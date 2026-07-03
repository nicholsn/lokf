.PHONY: all clean

# Reproduce every generated artifact from lokf.yaml, re-validate the reference
# bundle, and re-emit its RDF projection. Requires: pip install linkml rdflib pyyaml
all:
	python scripts/build.py

clean:
	rm -f examples/*.bundle.json examples/*.nt lokf.context.base.jsonld *.err
