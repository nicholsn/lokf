#!/usr/bin/env python3
"""Reproduce every generated LOKF artifact from the single source of truth
(``lokf.yaml``), then assemble the reference bundle, validate it against the
schema, and project it to RDF.

Run from anywhere inside the repository:

    uv sync
    uv run lokf-build               # or: just build

Outputs (regenerated in place):
    lokf.context.jsonld   JSON-LD context (+ type->@type, id->@id aliases)
    lokf.schema.json      JSON Schema
    lokf.shacl.ttl        SHACL shapes
    lokf.owl.ttl          OWL ontology
    examples/acme-knowledge.bundle.json   assembled bundle (git-ignored)
    examples/acme-knowledge.nt            RDF triples for the whole bundle
    examples/weekly-active-users.nt       RDF triples for one concept
"""
from __future__ import annotations
import json
import os
import pathlib
import shutil
import subprocess
import sys

from lokf.model import load_bundle


def _find_root() -> pathlib.Path:
    """Locate the repository root from the current directory or any ancestor.

    Requiring the reference bundle alongside ``lokf.yaml`` prevents the
    generators from writing into an unrelated directory that merely contains
    a file named ``lokf.yaml``.
    """
    cwd = pathlib.Path.cwd()
    for p in (cwd, *cwd.parents):
        if (p / "lokf.yaml").exists() and (p / "examples" / "acme-knowledge" / "index.md").exists():
            return p
    sys.exit(
        "lokf-build must be run from inside the lokf repository "
        "(no ancestor of the current directory contains both lokf.yaml "
        "and examples/acme-knowledge/)"
    )


def run(cmd, **kw):
    """Echo *cmd*, then run it with ``subprocess.run(..., check=True)``."""
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


def generate(root: pathlib.Path) -> None:
    """Run the four LinkML generators, then publish the authoring context."""
    schema = root / "lokf.yaml"
    print("== generate artifacts from lokf.yaml ==")
    with open(root / "lokf.schema.json", "w") as f:
        run(["gen-json-schema", str(schema)], stdout=f)
    with open(root / "lokf.owl.ttl", "w") as f:
        run(["gen-owl", str(schema)], stdout=f)
    with open(root / "lokf.shacl.ttl", "w") as f:
        run(["gen-shacl", str(schema)], stdout=f)

    base = root / "lokf.context.base.jsonld"
    with open(base, "w") as f:
        run(["gen-jsonld-context", str(schema)], stdout=f)
    ctx = json.load(open(base))
    # Two standard JSON-LD keyword aliases make unmodified OKF frontmatter
    # behave as Linked Data: `type` designates the RDF class, `id` the subject.
    ctx["@context"]["type"] = "@type"
    ctx["@context"]["id"] = "@id"
    ctx.setdefault("comments", {})["note"] = (
        "Authoring context: `type`->@type and `id`->@id aliased so OKF "
        "frontmatter is valid JSON-LD."
    )
    json.dump(ctx, open(root / "lokf.context.jsonld", "w"), indent=2)
    try:
        os.remove(base)  # gitignored intermediate; some filesystems block unlink
    except OSError:
        pass

    # Refresh the copies packaged with the lokf toolkit so an installed wheel
    # is self-sufficient (see lokf.schema's resolution order). Only when run
    # inside the lokf repo itself: a downstream knowledge repo that satisfies
    # _find_root must not have a src/lokf/ tree planted in it.
    outputs = "  -> lokf.context.jsonld, lokf.schema.json, lokf.shacl.ttl, lokf.owl.ttl"
    if (root / "src" / "lokf" / "__init__.py").exists():
        data = root / "src" / "lokf" / "data"
        data.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / "lokf.yaml", data / "lokf.yaml")
        shutil.copy(root / "lokf.context.jsonld", data / "lokf.context.jsonld")
        outputs += " (+ src/lokf/data copies)"
    print(outputs)


def assemble(root: pathlib.Path) -> dict:
    """Assemble all concept files (+ root index.md metadata) into one bundle."""
    b = load_bundle(root / "examples" / "acme-knowledge")
    bundle = dict(b.meta)
    concepts = b.docs()  # frontmatter + injected id (no-op where id is explicit)
    bundle["concepts"] = concepts
    json.dump(bundle, open(root / "examples" / "acme-knowledge.bundle.json", "w"), indent=2)
    print(f"== assembled bundle: {len(concepts)} concepts "
          f"({', '.join(c['type'] for c in concepts)}) ==")
    return bundle


def validate(root: pathlib.Path) -> None:
    """Validate the assembled bundle against the schema's ``KnowledgeBundle`` root."""
    print("== validate against JSON Schema ==")
    run(["linkml-validate", "-s", str(root / "lokf.yaml"), "-C", "KnowledgeBundle",
         str(root / "examples" / "acme-knowledge.bundle.json")])


def to_rdf(root: pathlib.Path, bundle: dict) -> None:
    """Project the bundle (and its Metric concept) to N-Triples in ``examples/``."""
    from rdflib import Graph
    ex = root / "examples"
    ctx = json.load(open(root / "lokf.context.jsonld"))["@context"]

    # Same single-parse projection as lokf.model.Bundle.graph(): the
    # assembled concepts already carry injected ids, so one @graph document
    # (context compiled once) covers the whole bundle.
    whole = Graph()
    whole.parse(
        data=json.dumps({"@context": ctx, "@graph": bundle["concepts"]}),
        format="json-ld",
    )
    whole.serialize(destination=str(ex / "acme-knowledge.nt"), format="nt")

    metric = next(c for c in bundle["concepts"] if c["type"] == "Metric")
    mdoc = {k: v for k, v in metric.items() if k != "body"}
    mdoc["@context"] = ctx
    mg = Graph()
    mg.parse(data=json.dumps(mdoc), format="json-ld")
    mg.serialize(destination=str(ex / "weekly-active-users.nt"), format="nt")
    print(f"== RDF projection: {len(whole)} triples (bundle), "
          f"{len(mg)} triples (metric) ==")


def main() -> int:
    """Entry point for the ``lokf-build`` console script."""
    root = _find_root()
    generate(root)
    bundle = assemble(root)
    validate(root)
    to_rdf(root, bundle)
    print("\nOK - all artifacts reproduced and validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
