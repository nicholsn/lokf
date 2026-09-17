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

    def duplicate_iris(self) -> list[tuple[str, list[str]]]:
        """IRIs that more than one file declares, each with those files' Concept IDs.

        A second file carrying an existing ``id`` - a sync client's conflict
        copy, a pasted duplicate, or an explicit ``id`` equal to another
        file's path-derived one - validates on its own and then merges into
        the first in :meth:`by_iri` and in the projected graph, where nothing
        can tell two subjects were meant. Only the loaded bundle, before that
        merge, can see it; the schema validates concepts one at a time.
        """
        files: dict[str, list[str]] = {}
        for c in self.concepts:
            files.setdefault(self.iri(c), []).append(c.concept_id)
        return [(iri, ids) for iri, ids in files.items() if len(ids) > 1]

    def get(self, ref: str) -> Concept | None:
        """Look up a concept by IRI, Concept ID, or bundle-relative path."""
        return self.by_iri().get(self.resolve(ref.removesuffix(".md")))


    _ABSOLUTE = ("http://", "https://", "urn:")

    def in_namespace(self, ref: str) -> bool:
        """Whether *ref* names something this bundle is responsible for.

        A relative ref (``metrics/wau``, ``/glossary/active-user.md``) always
        is - :meth:`resolve` mints it under ``base_iri``. An absolute IRI is
        only if it sits under ``base_iri``; anything else is an external
        resource, and a bundle cannot vouch for what it does not contain.
        """
        if ref.startswith(self._ABSOLUTE):
            return bool(self.base_iri) and ref.startswith(self.base_iri)
        return True

    def dangling_refs(
        self, schema_path: "str | pathlib.Path | None" = None
    ) -> list[tuple[str, str, str]]:
        """Typed-relation targets in this bundle's namespace that resolve to no concept.

        Covers every multivalued, ``Concept``-ranged slot the schema declares on
        ``Concept`` or a subclass (``isPartOf``, ``dependsOn``, ``about`` - see
        :class:`lokf.schema.Vocabulary`), plus the ``target`` of each reified
        entry under the generic ``relations`` slot, whose domain is ``Relation``
        rather than ``Concept`` and so is not in that set. JSON Schema cannot
        express this: a fabricated or stale IRI is a perfectly valid string.

        Only targets satisfying :meth:`in_namespace` are checked. Several
        relation slots are documented as taking an external resource -
        ``definedBy`` is "a resource that formally defines this concept",
        ``source`` "a resource from which this concept is derived" - so an
        off-site URL there is correct usage, not a broken link, and flagging it
        would make the check unusable on any bundle that cites the outside
        world.

        A target containing whitespace is skipped: some slots (``measures``)
        are documented as accepting a description instead of an IRI, and no
        valid IRI or bundle-relative path contains a space.

        ``schema_path`` should be the schema the caller validated against, so
        the relation vocabulary matches an explicit ``--schema``; the default
        resolves independently and may disagree with one.

        Returns ``(concept_id, slot, target)`` per unresolved target.
        """
        from lokf.schema import vocabulary

        def dangling(target: object) -> bool:
            return (
                isinstance(target, str)
                and bool(target.strip())
                and not any(ch.isspace() for ch in target)
                and self.in_namespace(target)
                and self.get(target) is None
            )

        out: list[tuple[str, str, str]] = []
        for slot in vocabulary(schema_path).relation_slots:
            for c in self.concepts:
                value = c.data.get(slot)
                if value is None:
                    continue
                for target in value if isinstance(value, list) else [value]:
                    if dangling(target):
                        out.append((c.concept_id, slot, target))
        for c in self.concepts:
            for relation in c.data.get("relations") or []:
                target = relation.get("target") if isinstance(relation, dict) else None
                if dangling(target):
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
