"""Load and represent LOKF knowledge bundles.

A bundle is a directory of markdown concept files (OKF layout). This module
lifts it into Python objects and, via the published JSON-LD context, into an
RDF graph::

    import lokf

    bundle = lokf.load_bundle("examples/acme-knowledge")
    g = bundle.graph()          # rdflib.Graph of the whole bundle
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

import yaml

from lokf.parse import isoify, parse_concept
from lokf.schema import load_context

RESERVED = ("index.md", "log.md")


@dataclass
class Concept:
    """One concept document: frontmatter ``data`` (with ``body``) plus its file."""

    path: pathlib.Path
    data: dict
    concept_id: str  # bundle-relative id, e.g. "metrics/weekly-active-users"

    @property
    def type(self) -> str:
        return self.data.get("type", "Concept")

    @property
    def title(self) -> str:
        return self.data.get("title", self.concept_id)

    @property
    def body(self) -> str:
        return self.data.get("body", "")


@dataclass
class Bundle:
    """A knowledge bundle: root ``index.md`` metadata plus its concepts."""

    root: pathlib.Path
    meta: dict
    concepts: list[Concept]

    @property
    def base_iri(self) -> str:
        return self.meta.get("base_iri", "")

    def resolve(self, ref: str) -> str:
        """Resolve a Concept ID or IRI to an absolute Concept IRI."""
        if ref.startswith(("http://", "https://", "urn:")):
            return ref
        return self.base_iri + ref.lstrip("/")

    def iri(self, concept: Concept) -> str:
        """A concept's IRI: explicit ``id`` or ``base_iri`` + Concept ID."""
        return concept.data.get("id") or self.resolve(concept.concept_id)

    def get(self, ref: str) -> Concept | None:
        """Look up a concept by IRI, Concept ID, or bundle-relative path."""
        target = self.resolve(ref.removesuffix(".md"))
        for c in self.concepts:
            if self.iri(c) == target:
                return c
        return None

    def to_jsonld(self, context: dict | None = None) -> list[dict]:
        """Each concept's frontmatter as a JSON-LD document (context attached)."""
        ctx = context if context is not None else load_context()
        docs = []
        for c in self.concepts:
            doc = dict(c.data)
            doc.setdefault("id", self.iri(c))
            doc["@context"] = ctx
            docs.append(doc)
        return docs

    def graph(self, context: dict | None = None):
        """The whole bundle as one :class:`rdflib.Graph`."""
        from rdflib import Graph

        g = Graph()
        for doc in self.to_jsonld(context):
            g.parse(data=json.dumps(doc), format="json-ld")
        return g


def load_bundle(path: str | pathlib.Path) -> Bundle:
    """Load a bundle directory into a :class:`Bundle`.

    ``index.md``/``log.md`` are reserved (OKF §3) and not parsed as concepts;
    the root ``index.md`` frontmatter becomes :attr:`Bundle.meta`.
    """
    root = pathlib.Path(path)
    meta: dict = {}
    index = root / "index.md"
    if index.exists():
        raw = index.read_text(encoding="utf-8")
        if raw.startswith("---"):
            meta = isoify(yaml.safe_load(raw.split("---", 2)[1])) or {}
    concepts = [
        Concept(
            path=p,
            data=parse_concept(str(p)),
            concept_id=p.relative_to(root).with_suffix("").as_posix(),
        )
        for p in sorted(root.rglob("*.md"))
        if p.name not in RESERVED
    ]
    return Bundle(root=root, meta=meta, concepts=concepts)
