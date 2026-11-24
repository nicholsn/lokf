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
import os
import pathlib
from dataclasses import dataclass

from linkml_runtime.utils.formatutils import underscore

from lokf.parse import parse_concept_fields, parse_index_text, read_markdown
from lokf.schema import SchemaSource, load_context

RESERVED = ("index.md", "log.md")


@dataclass
class Concept:
    """One concept document: frontmatter ``data`` (with ``body``) plus its file."""

    path: pathlib.Path
    data: dict
    concept_id: str  # bundle-relative id, e.g. "metrics/weekly-active-users"
    authored_mappings: tuple[str, ...] = ()

    @property
    def type(self) -> str:
        return self.data.get("type", "Concept")

    @property
    def title(self) -> str:
        return self.data.get("title", self.concept_id)

    @property
    def body(self) -> str:
        return self.data.get("body", "")


    def reference_values(self, slot: str) -> list:
        """Read the authored or LinkML-normalized key, in either cardinality."""
        value = self.data.get(slot)
        if value is None:
            value = self.data.get(underscore(slot))
        if value is None:
            return []
        return value if isinstance(value, list) else [value]


def _is_curie(ref: str) -> bool:
    """``prefix:local`` with a scheme-like prefix: what JSON-LD reads as a
    compact IRI rather than a relative one. An absolute IRI is not one."""
    prefix, sep, local = ref.partition(":")
    return bool(sep and local and prefix) and "/" not in prefix and not ref.startswith(Bundle._ABSOLUTE)


@dataclass
class Bundle:
    """A knowledge bundle: root ``index.md`` metadata plus its concepts."""

    root: pathlib.Path
    meta: dict
    concepts: list[Concept]

    @property
    def base_iri(self) -> str:
        base = self.meta.get("base_iri")
        # Keep the authored value in meta for validation. Only strings can resolve IDs.
        return base if isinstance(base, str) else ""

    def resolve(self, ref: str) -> str:
        """Resolve a Concept ID or IRI to an absolute Concept IRI."""
        if ref.startswith(("http://", "https://", "urn:")):
            return ref
        return self.base_iri + ref.lstrip("/")

    def iri(self, concept: Concept) -> str:
        """A concept's IRI: explicit ``id`` or ``base_iri`` + Concept ID."""
        value = concept.data.get("id")
        return value if isinstance(value, str) and value else self.resolve(concept.concept_id)

    def _declared_iris(self):
        for concept in self.concepts:
            # A malformed explicit id cannot declare a target under the file's name.
            if isinstance(concept.data.get("id", ""), str):
                yield self.iri(concept), concept

    def by_iri(self) -> dict[str, Concept]:
        """IRI -> Concept index (built once, cached)."""
        if not hasattr(self, "_by_iri"):
            self._by_iri = dict(self._declared_iris())
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
        for iri, concept in self._declared_iris():
            files.setdefault(iri, []).append(concept.concept_id)
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

        Covers every slot a ``Concept`` class holds concept ids in, single- or
        multivalued (``isPartOf``, ``dependsOn``, ``about`` - see
        :attr:`lokf.schema.Vocabulary.reference_slots`), plus the ``target`` of
        each reified entry under the generic ``relations`` slot, whose domain
        is ``Relation`` rather than ``Concept`` and so is not in that set. JSON
        Schema cannot express this: a fabricated or stale IRI is a perfectly
        valid string.

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

        vocab = vocabulary(schema_path)

        def dangling(target: object) -> bool:
            if not (
                isinstance(target, str)
                and bool(target.strip())
                and not any(ch.isspace() for ch in target)
            ):
                return False
            # A `prefix:local` target is a CURIE, never a relative ref: JSON-LD
            # reads a colon in `@id` as an IRI. It is the IRI it expands to
            # under a prefix the schema declares, and under one it does not
            # (biolink leaves `NCBITaxon:9606` to LinkML's default CURIE maps)
            # it is at any rate not this bundle's to resolve.
            expanded = vocab.expand(target)
            if expanded == target and _is_curie(target):
                return False
            return self.in_namespace(expanded) and self.get(expanded) is None

        out: list[tuple[str, str, str]] = []
        slots_by_type: dict[str, list[str]] = {}
        for c in self.concepts:
            # Only the slots that hold concept ids on this concept's type: a
            # class can narrow an inherited reference slot to a string.
            type_name = c.type
            if not isinstance(type_name, str) or type_name not in vocab.classes:
                type_name = "Concept"
            if type_name not in slots_by_type:
                slots_by_type[type_name] = sorted(vocab.references(type_name))
            for slot in slots_by_type[type_name]:
                for target in c.reference_values(slot):
                    if dangling(target):
                        out.append((c.concept_id, slot, target))
        for c in self.concepts:
            relations = c.data.get("relations")
            if not isinstance(relations, list):
                continue
            for relation in relations:
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

    def graph(self, context: dict | None = None, schema: SchemaSource = None):
        """The whole bundle as one :class:`rdflib.Graph`, under the domain
        vocabulary *schema* when one is given.

        All concepts are parsed in a single pass (one ``@graph`` document) so
        the JSON-LD context is compiled once, not once per concept.
        """
        from lokf.rdf import docs_to_graph

        return docs_to_graph(self.docs(), context, base=self.base_iri or None, schema=schema)


def _markdown_files(root):
    """Enumerate all Markdown input. A failed scan must reach the caller."""
    files = []
    pending = [root]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                path = pathlib.Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                if path.match("*.md"):
                    files.append(path)
    return sorted(files)


def load_bundle(path: str | pathlib.Path) -> Bundle:
    """Load a bundle directory into a :class:`Bundle`.

    ``index.md``/``log.md`` are reserved (OKF §3) and not parsed as concepts;
    the root ``index.md`` frontmatter becomes :attr:`Bundle.meta`.
    """
    root = pathlib.Path(path)
    return _load_bundle_files(root, sorted(root.rglob("*.md")), (root / "index.md").exists())


def _load_bundle_files(root, markdown_files, has_index, read=read_markdown):
    meta: dict = {}
    index = root / "index.md"
    if has_index:
        meta = parse_index_text(read(index), str(index))
    concepts = []
    for p in markdown_files:
        if p.name not in RESERVED:
            data, mappings = parse_concept_fields(read(p), str(p))
            concepts.append(Concept(p, data, p.relative_to(root).with_suffix("").as_posix(), mappings))
    return Bundle(root=root, meta=meta, concepts=concepts)
