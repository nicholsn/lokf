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
    lokf.sql              relational schema (CREATE TABLE DDL)
    src/lokf/datamodel.py LinkML dataclass bindings (from lokf.datamodel import ...)
    examples/acme-knowledge.bundle.json   assembled bundle (git-ignored)
    examples/acme-knowledge.nt            RDF triples for the whole bundle
    examples/weekly-active-users.nt       RDF triples for one concept
"""
from __future__ import annotations
import json
import os
import pathlib
import re
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



# ---------------------------------------------------------------------------
# determinism
#
# The LinkML generators are not reproducible: re-running them over an
# unmodified lokf.yaml rewrote ~2,575 lines across the committed artifacts,
# which buried every real schema diff and made it impossible for CI to assert
# that the artifacts match their source. Three distinct causes, each corrected
# below so `lokf-build` is byte-stable and `ci/generated-fresh` can gate it.
# ---------------------------------------------------------------------------

#: Predicates whose rdf:List value is semantically a *set*. LinkML builds these
#: lists by iterating a Python set, so member order varies per run; sorting them
#: is meaning-preserving. Ordered lists MUST NOT be added here.
_SET_VALUED_LISTS = ("http://www.w3.org/ns/shacl#ignoredProperties",)


def _sort_set_valued_lists(g) -> None:
    """Sort the members of every set-valued rdf:List in *g*, in place."""
    from rdflib import BNode, URIRef
    from rdflib.collection import Collection

    for pred in _SET_VALUED_LISTS:
        for _s, _p, head in list(g.triples((None, URIRef(pred), None))):
            if not isinstance(head, BNode):
                continue
            coll = Collection(g, head)
            members = sorted(coll, key=str)
            if list(coll) != members:
                coll.clear()
                for m in members:
                    coll.append(m)


def _relabel_bnodes(g):
    """Return a copy of *g* whose blank-node labels are derived from content.

    rdflib mints blank-node ids from uuid4, so identical input yields different
    labels every run. Each node is hashed from its own incoming and outgoing
    edges, iterated to a fixpoint so nested blank nodes converge; structurally
    indistinguishable nodes then get a stable index. This only renames blank
    nodes - no triple is added, dropped or rewritten.

    (rdflib's own ``to_canonical_graph`` is not usable here: on these
    almost-entirely-blank-node SHACL graphs it returns different labels for the
    same content, the same weakness that makes ``to_isomorphic`` report a false
    negative on lokf.shacl.ttl.)
    """
    import hashlib
    from rdflib import BNode, Graph

    labels = {n: "0" for n in g.all_nodes() if isinstance(n, BNode)}
    for _ in range(12):
        nxt = {}
        for b in labels:
            out = sorted((str(p), labels.get(o, str(o))) for _, p, o in g.triples((b, None, None)))
            inc = sorted((labels.get(s, str(s)), str(p)) for s, p, _ in g.triples((None, None, b)))
            nxt[b] = hashlib.sha256(repr((out, inc)).encode()).hexdigest()[:24]
        if nxt == labels:
            break
        labels = nxt

    buckets: dict = {}
    for b, h in sorted(labels.items(), key=lambda kv: (kv[1], str(kv[0]))):
        buckets.setdefault(h, []).append(b)
    mapping = {b: BNode(f"x{h}{i}") for h, bs in buckets.items() for i, b in enumerate(bs)}

    out_g = Graph()
    for prefix, ns in g.namespaces():
        out_g.bind(prefix, ns)
    for s, p, o in g:
        out_g.add((mapping.get(s, s), p, mapping.get(o, o)))
    return out_g


def _canonicalize_rdf(path: pathlib.Path, fmt: str, header: str = "") -> None:
    """Rewrite *path* so the same graph always serializes to the same bytes.

    *header* is re-emitted as leading comments: re-serializing a graph drops
    the source file's comments, so any provenance note worth keeping must be
    passed here rather than written into the generated text.
    """
    from rdflib import Graph

    g = Graph().parse(str(path), format=fmt)
    before = len(g)
    _sort_set_valued_lists(g)
    text = _relabel_bnodes(g).serialize(format=fmt)
    if fmt == "nt":
        # N-Triples has no grouping, so line order is the only variable left.
        text = "\n".join(sorted(t for t in text.splitlines() if t.strip())) + "\n"
    path.write_text(header + text, encoding="utf-8")
    after = len(Graph().parse(str(path), format=fmt))
    if after != before:
        sys.exit(f"canonicalization changed {path.name}: {before} -> {after} triples")


def _sort_sql_indexes(path: pathlib.Path) -> None:
    """Sort the trailing CREATE INDEX block of the generated DDL.

    gen-sqltables emits CREATE TABLE in a stable order but CREATE INDEX in a
    varying one. Indexes are order-independent, so sorting them is safe.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = [l for l in lines if l.startswith("CREATE INDEX")]
    if not idx:
        return
    rest = [l for l in lines if not l.startswith("CREATE INDEX")]
    while rest and not rest[-1].strip():
        rest.pop()
    path.write_text("\n".join(rest + sorted(idx)) + "\n", encoding="utf-8")


def generate(root: pathlib.Path) -> None:
    """Run the four LinkML generators, then publish the authoring context."""
    schema = root / "lokf.yaml"
    print("== generate artifacts from lokf.yaml ==")
    with open(root / "lokf.schema.json", "w") as f:
        run(["gen-json-schema", str(schema)], stdout=f)
    with open(root / "lokf.owl.ttl", "w") as f:
        run(["gen-owl", str(schema)], stdout=f)
    # LinkML materializes enum meanings as IRIs but does not declare class
    # axioms for them: assert each Parameter-kind class (ParameterType
    # meanings) as a subclass of lokf:Parameter with its XSD value space, and
    # lokf:Verification as a subclass of prov:Activity (its class_uri is
    # lokf-minted; the PROV alignment lives here).
    with open(root / "lokf.owl.ttl", "a") as f:
        f.write(
            "\n### OKF v0.2 post-generation axioms (lokf-build) ###\n"
            "@prefix lokf: <https://w3id.org/lokf/> .\n"
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
            "@prefix prov: <http://www.w3.org/ns/prov#> .\n\n"
            "lokf:Verification rdfs:subClassOf prov:Activity .\n\n"
        )
        for cls, space in {
            "StringParameter": "xsd:string", "IntegerParameter": "xsd:integer",
            "NumberParameter": "xsd:decimal", "BooleanParameter": "xsd:boolean",
            "DateParameter": "xsd:date", "DatetimeParameter": "xsd:dateTime",
            "TimeParameter": "xsd:time", "UriParameter": "xsd:anyURI",
            "JsonParameter": "rdf:JSON",
        }.items():
            f.write(
                f"lokf:{cls} a owl:Class ;\n"
                f"    rdfs:subClassOf lokf:Parameter ;\n"
                f"    lokf:xsd_value_space {space} .\n"
            )
    _canonicalize_rdf(
        root / "lokf.owl.ttl", "turtle",
        header=(
            "# Generated by lokf-build from lokf.yaml (gen-owl), then extended\n"
            "# with the OKF v0.2 post-generation axioms: lokf:Verification as a\n"
            "# subclass of prov:Activity, and each ParameterType meaning as a\n"
            "# lokf:Parameter subclass carrying its XSD value space.\n"
            "# Blank-node labels are content-derived so this file is byte-stable.\n\n"
        ),
    )

    with open(root / "lokf.shacl.ttl", "w") as f:
        run(["gen-shacl", str(schema)], stdout=f)
    _canonicalize_rdf(root / "lokf.shacl.ttl", "turtle")

    # The relational projection of the schema: CREATE TABLE DDL with foreign
    # keys auto-created for the typed relations. The instance-level counterpart
    # (a bundle -> linked DataFrames/SQL) lives in ``lokf.tables``.
    with open(root / "lokf.sql", "w") as f:
        run(["gen-sqltables", str(schema)], stdout=f)
    _sort_sql_indexes(root / "lokf.sql")

    base = root / "lokf.context.base.jsonld"
    with open(base, "w") as f:
        run(["gen-jsonld-context", str(schema)], stdout=f)
    ctx = json.load(open(base))
    # Two standard JSON-LD keyword aliases make unmodified OKF frontmatter
    # behave as Linked Data: `type` designates the RDF class, `id` the subject.
    ctx["@context"]["type"] = "@type"
    ctx["@context"]["id"] = "@id"
    # ParameterType values sit in @type position (Parameter's `type` key shares
    # the alias above), so each authoring value must expand to its designed
    # lokf Parameter-kind class — gen-jsonld-context does not emit enum-meaning
    # terms. Same mechanism by which class names like "Metric" expand as @type.
    for value, cls in {
        "string": "StringParameter", "integer": "IntegerParameter",
        "number": "NumberParameter", "boolean": "BooleanParameter",
        "date": "DateParameter", "datetime": "DatetimeParameter",
        "time": "TimeParameter", "uri": "UriParameter", "json": "JsonParameter",
    }.items():
        ctx["@context"][value] = {"@id": f"https://w3id.org/lokf/{cls}"}
    # `author` must NOT be @id-coerced: OKF §7 actor strings ("team:ga4-docs",
    # "human:kliu") are literals, and coercion would silently mint IRIs in
    # unregistered URI schemes. Inlined Agent objects are unaffected.
    if isinstance(ctx["@context"].get("author"), dict):
        ctx["@context"]["author"].pop("@type", None)
    # A wall-clock stamp on a committed artifact is pure churn - git already
    # records when it changed - and it is the only volatile field here.
    ctx.get("comments", {}).pop("generation_date", None)
    ctx.setdefault("comments", {})["note"] = (
        "Authoring context: `type`->@type and `id`->@id aliased so OKF "
        "frontmatter is valid JSON-LD; ParameterType values expand to "
        "lokf Parameter-kind classes; `author` is uncoerced (actor strings "
        "are literals)."
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
    outputs = "  -> lokf.context.jsonld, lokf.schema.json, lokf.shacl.ttl, lokf.owl.ttl, lokf.sql"
    if (root / "src" / "lokf" / "__init__.py").exists():
        data = root / "src" / "lokf" / "data"
        data.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / "lokf.yaml", data / "lokf.yaml")
        shutil.copy(root / "lokf.context.jsonld", data / "lokf.context.jsonld")
        # Typed Python bindings for the vocabulary: `from lokf.datamodel import
        # Metric`, etc. LinkML dataclasses (backed by linkml_runtime) that
        # validate required fields and round-trip to JSON / YAML / RDF.
        # Committed so an installed wheel ships them.
        with open(root / "src" / "lokf" / "datamodel.py", "w") as f:
            run(["gen-python", str(schema)], stdout=f)
        # The OKF v0.2 `from` slot (UsageWindow.from) is a Python keyword;
        # gen-python emits it verbatim, which is a SyntaxError. Alias the
        # generated attribute to `from_` — the YAML key and JSON-LD term
        # stay `from`.
        dm = root / "src" / "lokf" / "datamodel.py"
        text = dm.read_text(encoding="utf-8")
        # `self.from` accesses and the `from:`-annotated dataclass field, in
        # code positions only (docstrings/comments talk about "from" freely).
        patched = re.sub(r"\b(\w+)\.from\b", r"\1.from_", text)  # self.from, slots.from
        patched = re.sub(r"^(\s+)from(: .*=.*)$", r"\1from_\2", patched, flags=re.M)
        # Reconstruction call sites rebuild UsageWindow from raw dicts still
        # keyed `from` (the YAML/JSON-LD term); rename the key at the call.
        patched = patched.replace(
            "UsageWindow(**as_dict(self.usage_window))",
            'UsageWindow(**{("from_" if k == "from" else k): v'
            " for k, v in as_dict(self.usage_window).items()})",
        )
        # Same volatile stamp as the context above; the rest of the generated
        # header (source schema, id, description, license) is kept.
        patched = re.sub(r"^# Generation date: .*\n", "", patched, flags=re.M)
        if patched != text:
            dm.write_text(patched, encoding="utf-8")
        compile(dm.read_text(encoding="utf-8"), str(dm), "exec")  # fail loudly
        outputs += " (+ src/lokf/data copies + datamodel.py)"
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
    base = bundle.get("base_iri") or None  # anchors relative @ids (sources[].id)
    whole = Graph()
    whole.parse(
        data=json.dumps({"@context": ctx, "@graph": bundle["concepts"]}),
        format="json-ld",
        publicID=base,
    )
    whole.serialize(destination=str(ex / "acme-knowledge.nt"), format="nt")
    _canonicalize_rdf(ex / "acme-knowledge.nt", "nt")

    metric = next(c for c in bundle["concepts"] if c["type"] == "Metric")
    mdoc = {k: v for k, v in metric.items() if k != "body"}
    mdoc["@context"] = ctx
    mg = Graph()
    mg.parse(data=json.dumps(mdoc), format="json-ld", publicID=base)
    mg.serialize(destination=str(ex / "weekly-active-users.nt"), format="nt")
    _canonicalize_rdf(ex / "weekly-active-users.nt", "nt")
    print(f"== RDF projection: {len(whole)} triples (bundle), "
          f"{len(mg)} triples (metric) ==")


def main() -> int:
    """Entry point for the ``lokf-build`` console script."""
    root = _find_root()
    # generate() opens each artifact for writing *before* its generator runs, so
    # a missing generator would truncate a committed artifact on the way to a
    # traceback. Check once, up front.
    if shutil.which("gen-json-schema") is None:
        sys.exit(
            "the LinkML generators are not on PATH: lokf-build needs the "
            "`build` extra.\n  install:  uv sync   "
            "(or: uv pip install 'lokf[build]')"
        )
    generate(root)
    bundle = assemble(root)
    validate(root)
    to_rdf(root, bundle)
    print("\nOK - all artifacts reproduced and validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
