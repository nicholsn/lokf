#!/usr/bin/env python3
"""Reproduce every generated LOKF artifact from the single source of truth
(``lokf.yaml``), then assemble the reference bundle, validate it against the
schema, and project it to RDF.

    pip install linkml rdflib pyyaml
    python scripts/build.py         # or: make

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
import datetime as dt
import glob
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "lokf.yaml"
EX = ROOT / "examples"
BUNDLE_DIR = EX / "acme-knowledge"


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


def generate() -> None:
    """Run the four LinkML generators, then publish the authoring context."""
    print("== generate artifacts from lokf.yaml ==")
    with open(ROOT / "lokf.schema.json", "w") as f:
        run(["gen-json-schema", str(SCHEMA)], stdout=f)
    with open(ROOT / "lokf.owl.ttl", "w") as f:
        run(["gen-owl", str(SCHEMA)], stdout=f)
    with open(ROOT / "lokf.shacl.ttl", "w") as f:
        run(["gen-shacl", str(SCHEMA)], stdout=f)

    base = ROOT / "lokf.context.base.jsonld"
    with open(base, "w") as f:
        run(["gen-jsonld-context", str(SCHEMA)], stdout=f)
    ctx = json.load(open(base))
    # Two standard JSON-LD keyword aliases make unmodified OKF frontmatter
    # behave as Linked Data: `type` designates the RDF class, `id` the subject.
    ctx["@context"]["type"] = "@type"
    ctx["@context"]["id"] = "@id"
    ctx.setdefault("comments", {})["note"] = (
        "Authoring context: `type`->@type and `id`->@id aliased so OKF "
        "frontmatter is valid JSON-LD."
    )
    json.dump(ctx, open(ROOT / "lokf.context.jsonld", "w"), indent=2)
    try:
        os.remove(base)  # gitignored intermediate; some filesystems block unlink
    except OSError:
        pass
    print("  -> lokf.context.jsonld, lokf.schema.json, lokf.shacl.ttl, lokf.owl.ttl")


def _isoify(o):
    if isinstance(o, dict):
        return {k: _isoify(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_isoify(v) for v in o]
    if isinstance(o, (dt.datetime, dt.date)):
        return o.isoformat().replace("+00:00", "Z")
    return o


def _parse_concept(path: str) -> dict:
    import yaml
    raw = open(path, encoding="utf-8").read()
    _, front, body = raw.split("---", 2)
    d = yaml.safe_load(front) or {}
    d["body"] = body.strip()
    return _isoify(d)


def assemble() -> dict:
    """Assemble all concept files (+ root index.md metadata) into one bundle."""
    import yaml
    idx = open(BUNDLE_DIR / "index.md", encoding="utf-8").read().split("---", 2)
    bundle = _isoify(yaml.safe_load(idx[1]))
    concepts = [
        _parse_concept(p)
        for p in sorted(glob.glob(str(BUNDLE_DIR / "**" / "*.md"), recursive=True))
        if os.path.basename(p) not in ("index.md", "log.md")
    ]
    bundle["concepts"] = concepts
    json.dump(bundle, open(EX / "acme-knowledge.bundle.json", "w"), indent=2)
    print(f"== assembled bundle: {len(concepts)} concepts "
          f"({', '.join(c['type'] for c in concepts)}) ==")
    return bundle


def validate() -> None:
    print("== validate against JSON Schema ==")
    run(["linkml-validate", "-s", str(SCHEMA), "-C", "KnowledgeBundle",
         str(EX / "acme-knowledge.bundle.json")])


def to_rdf(bundle: dict) -> None:
    from rdflib import Graph
    ctx = json.load(open(ROOT / "lokf.context.jsonld"))["@context"]

    whole = Graph()
    for c in bundle["concepts"]:
        doc = dict(c)
        doc["@context"] = ctx
        whole.parse(data=json.dumps(doc), format="json-ld")
    whole.serialize(destination=str(EX / "acme-knowledge.nt"), format="nt")

    metric = next(c for c in bundle["concepts"] if c["type"] == "Metric")
    mdoc = {k: v for k, v in metric.items() if k != "body"}
    mdoc["@context"] = ctx
    mg = Graph()
    mg.parse(data=json.dumps(mdoc), format="json-ld")
    mg.serialize(destination=str(EX / "weekly-active-users.nt"), format="nt")
    print(f"== RDF projection: {len(whole)} triples (bundle), "
          f"{len(mg)} triples (metric) ==")


def main() -> int:
    generate()
    bundle = assemble()
    validate()
    to_rdf(bundle)
    print("\nOK - all artifacts reproduced and validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
