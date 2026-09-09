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

    def by_iri(self) -> dict[str, Concept]:
        """IRI -> Concept index (built once, cached)."""
        if not hasattr(self, "_by_iri"):
            self._by_iri = {self.iri(c): c for c in self.concepts}
        return self._by_iri

    def get(self, ref: str) -> Concept | None:
        """Look up a concept by IRI, Concept ID, or bundle-relative path."""
        return self.by_iri().get(self.resolve(ref.removesuffix(".md")))

    def dangling_refs(
        self, schema_path: str | pathlib.Path | None = None
    ) -> list[tuple[str, str, str]]:
        """Typed-relation targets that resolve to no concept in the bundle.

        Checks every multivalued, ``Concept``-ranged slot the schema declares
        on ``Concept`` or a subclass (``isPartOf``, ``dependsOn``, ``about``,
        etc. - see :class:`lokf.schema.Vocabulary`), plus the ``target`` of
        each reified entry under the generic ``relations`` slot, which the
        vocabulary's own domain scoping excludes (its domain is ``Relation``,
        not ``Concept``). This closes a gap schema validation cannot cover.

        ``schema_path`` should be the same schema the caller validated
        against (e.g. ``validate``'s resolved ``--schema``) so the relation
        vocabulary matches - the default (``None``) resolves independently
        and may disagree with an explicit ``--schema``.

        A target containing whitespace is skipped rather than flagged; some
        relation slots are documented as accepting a description instead of
        a concept IRI, but no valid IRI or bundle-relative path contains space.

        Returns a list of ``(concept_id, slot, target)`` triples, one per
        unresolved target.
        """
        from lokf.schema import vocabulary

        def is_dangling(target: object) -> bool:
            return (
                isinstance(target, str)
                and not any(ch.isspace() for ch in target)
                and self.get(target) is None
            )

        relation_slots = vocabulary(schema_path).relation_slots
        out: list[tuple[str, str, str]] = []
        for c in self.concepts:
            for slot in relation_slots:
                value = c.data.get(slot)
                if value is None:
                    continue
                for target in value if isinstance(value, list) else [value]:
                    if is_dangling(target):
                        out.append((c.concept_id, slot, target))
            for relation in c.data.get("relations") or []:
                target = relation.get("target") if isinstance(relation, dict) else None
                if is_dangling(target):
                    out.append((c.concept_id, "relations", target))
        return out

    def docs(self) -> list[dict]:
        """Each concept's frontmatter with its IRI injected as ``id``."""
        out = []
        for c in self.concepts:
            doc = dict(c.data)
            doc.setdefault("id", self.iri(c))
            out.append(doc)
        return out

    def to_jsonld(self, context: dict | None = None) -> list[dict]:
        """Each concept's frontmatter as a JSON-LD document (context attached)."""
        ctx = context if context is not None else load_context()
        return [{**doc, "@context": ctx} for doc in self.docs()]

    def graph(self, context: dict | None = None):
        """The whole bundle as one :class:`rdflib.Graph`.

        All concepts are parsed in a single pass (one ``@graph`` document) so
        the JSON-LD context is compiled once, not once per concept.
        """
        from lokf.rdf import docs_to_graph

        return docs_to_graph(self.docs(), context, base=self.base_iri or None)


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
