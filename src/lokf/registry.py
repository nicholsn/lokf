"""Cross-bundle federation: a registry of LOKF bundles (*meta-lokf*).

A registry (``lokf-registry.yaml``) maps each member bundle's ``base_iri`` to
where its exported artifacts and source documents live. The one load-bearing
operation is :meth:`Registry.owner` — longest-``base_iri``-prefix routing, the
exact inverse of :meth:`lokf.model.Bundle.iri` minting — so following an IRI
from one bundle into another is pure string math: no network, no shared
database. See SPEC §11.

This module is the offline core (Phase 1): loading/saving the manifest,
building an entry from a local bundle, and resolving an IRI to its owning
bundle + Concept ID + source URL. Harvesting remote artifacts and traversing a
federated store land in later phases.
"""
from __future__ import annotations

import dataclasses
import pathlib
from collections import Counter
from dataclasses import dataclass, field

import yaml

#: The ontology ``@vocab``. Never a repo ``base_iri`` — an IRI under it that no
#: (strictly longer) member owns is a vocabulary term, not a foreign concept.
VOCAB_NS = "https://w3id.org/lokf/"
REGISTRY_VERSION = "0.1"
DEFAULT_REGISTRY = "lokf-registry.yaml"


@dataclass
class RepoEntry:
    """One member bundle. ``base_iri`` is its identity and routing key."""

    base_iri: str
    title: str = ""
    repo: str | None = None
    source_base: str = ""
    path: str | None = None
    distribution: dict = field(default_factory=dict)
    void: dict = field(default_factory=dict)
    id_index: dict = field(default_factory=dict)  # explicit-id IRI -> Concept ID
    sensitivity: str | None = None
    status: str = "ok"


@dataclass
class Resolution:
    """The result of resolving an IRI against a registry."""

    iri: str
    entry: RepoEntry | None
    concept_id: str | None
    source_url: str | None
    via: str | None  # "prefix" | "id_index" | None

    @property
    def external(self) -> bool:
        """True when no member owns the IRI (a tolerated dangling link)."""
        return self.entry is None


def _source_url(entry: RepoEntry, concept_id: str | None) -> str | None:
    """A concept's source-markdown URL: ``source_base``/``concept_id``.md.

    Returns ``None`` when the entry has no ``source_base`` or the IRI is the
    bundle's namespace root (empty Concept ID) — neither names a document.
    """
    if not entry.source_base or not concept_id:
        return None
    return entry.source_base.rstrip("/") + "/" + concept_id + ".md"


@dataclass
class Registry:
    """A registry of LOKF bundles, loaded from ``lokf-registry.yaml``."""

    path: pathlib.Path
    id: str = ""
    title: str = ""
    publisher: dict = field(default_factory=dict)
    version: str = REGISTRY_VERSION
    repos: list[RepoEntry] = field(default_factory=list)

    # -- resolution ---------------------------------------------------------
    def _match(self, iri: str) -> tuple[RepoEntry | None, str | None, str | None]:
        """(entry, via, concept_id) for *iri*, or (None, None, None).

        Longest-``base_iri``-prefix wins; an explicit-``id`` in an ``id_index``
        is only a *fallback* for an IRI that no base_iri prefixes (SPEC §11
        rule 1), so a stale index entry can never hijack an IRI a member owns by
        prefix.
        """
        best: RepoEntry | None = None
        for e in self.repos:
            if e.base_iri and iri.startswith(e.base_iri):
                if best is None or len(e.base_iri) > len(best.base_iri):
                    best = e
        if best is not None:
            return best, "prefix", iri[len(best.base_iri):].lstrip("/")
        for e in self.repos:
            if iri in e.id_index:
                return e, "id_index", e.id_index[iri]
        return None, None, None

    def owner(self, iri: str) -> RepoEntry | None:
        """The member bundle that owns *iri*, or ``None`` if external."""
        return self._match(iri)[0]

    def resolve(self, iri: str) -> Resolution:
        """Resolve *iri* to its owning bundle, Concept ID, and source URL."""
        entry, via, concept_id = self._match(iri)
        return Resolution(
            iri=iri,
            entry=entry,
            concept_id=concept_id,
            source_url=_source_url(entry, concept_id) if entry else None,
            via=via,
        )

    # -- mutation -----------------------------------------------------------
    def add(self, entry: RepoEntry) -> None:
        """Validate and append *entry*. Raises ``ValueError`` on conflict.

        A base_iri must be non-empty, end in a path separator (``/`` or ``#``)
        so prefix routing respects segment boundaries (``…/team/`` never
        captures ``…/team-archive/``), stay clear of the vocabulary namespace,
        and neither duplicate nor nest with an existing member (either would
        make routing ambiguous).
        """
        b = entry.base_iri
        if not b:
            raise ValueError("entry has no base_iri")
        if not b.endswith(("/", "#")):
            raise ValueError(f"base_iri must end with '/' or '#': {b!r}")
        if VOCAB_NS.startswith(b):
            raise ValueError(
                f"base_iri {b!r} captures the vocabulary namespace {VOCAB_NS}; "
                "a member base_iri must be strictly longer"
            )
        for e in self.repos:
            if e.base_iri == b:
                raise ValueError(f"base_iri already registered: {b}")
            if b.startswith(e.base_iri) or e.base_iri.startswith(b):
                raise ValueError(
                    f"base_iri {b!r} nests with registered {e.base_iri!r}; "
                    "base_iris must not be prefixes of one another"
                )
        self.repos.append(entry)

    def to_dict(self) -> dict:
        """The manifest as a plain dict for YAML serialization."""
        d: dict = {"lokf_registry_version": self.version, "type": "dcat:Catalog"}
        if self.id:
            d["id"] = self.id
        if self.title:
            d["title"] = self.title
        if self.publisher:
            d["publisher"] = self.publisher
        d["repos"] = [_entry_dict(e) for e in self.repos]
        return d

    def save(self) -> None:
        """Write the manifest back to :attr:`path` (block-style YAML)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


_FIELDS = dataclasses.fields(RepoEntry)
_ENTRY_FIELDS = {f.name for f in _FIELDS}
_ENTRY_DEFAULTS = {
    f.name: (f.default_factory() if f.default_factory is not dataclasses.MISSING else f.default)
    for f in _FIELDS
}


def _entry_dict(entry: RepoEntry) -> dict:
    """A RepoEntry as a dict, dropping fields left at their default value."""
    out = {}
    for k, v in dataclasses.asdict(entry).items():
        if k != "base_iri" and v == _ENTRY_DEFAULTS.get(k):
            continue
        out[k] = v
    return out


def load_registry(path: str | pathlib.Path) -> Registry:
    """Load ``lokf-registry.yaml`` with a plain YAML reader (no LinkML).

    Tolerant of a hand-edited manifest: a null ``repos:`` or null field values
    fall back to defaults rather than crashing a later lookup.
    """
    p = pathlib.Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{p}: registry must be a YAML mapping, got {type(data).__name__}")
    entries = data.get("repos") or []
    if not isinstance(entries, list):
        raise ValueError(f"{p}: 'repos' must be a list")
    repos = [
        RepoEntry(**{k: v for k, v in (r or {}).items() if k in _ENTRY_FIELDS and v is not None})
        for r in entries
    ]
    return Registry(
        path=p,
        id=data.get("id") or "",
        title=data.get("title") or "",
        publisher=data.get("publisher") or {},
        version=str(data.get("lokf_registry_version") or REGISTRY_VERSION),
        repos=repos,
    )


def entry_for_bundle(
    bundle_dir: str | pathlib.Path,
    source_base: str | None = None,
) -> RepoEntry:
    """Build a :class:`RepoEntry` from a local bundle directory.

    Derives ``base_iri``/``title``/``publisher`` from the bundle's ``index.md``,
    computes a VoID planning index (triple + per-type counts), and harvests an
    ``id_index`` of explicit-``id`` IRIs that diverge from ``base_iri`` +
    Concept ID (so they still route). Raises ``ValueError`` if the bundle has
    no ``base_iri`` or a concept IRI falls outside it and is not indexable.
    """
    from lokf.model import load_bundle

    bundle = load_bundle(bundle_dir)
    base_iri = bundle.base_iri
    if not base_iri:
        raise ValueError(f"{bundle_dir}: bundle index.md has no base_iri; cannot federate")

    id_index: dict[str, str] = {}
    for c in bundle.concepts:
        actual = bundle.iri(c)
        if actual != base_iri + c.concept_id:  # explicit id diverges from the mint rule
            id_index[actual] = c.concept_id

    # Ownership: every concept IRI must be routable (under base_iri or indexed).
    for iri in bundle.by_iri():
        if not iri.startswith(base_iri) and iri not in id_index:
            raise ValueError(
                f"concept IRI {iri} is outside base_iri {base_iri} and not indexable"
            )

    part = Counter(c.type for c in bundle.concepts)
    void = {"triples": len(bundle.graph()), "class_partition": dict(part)}

    root = pathlib.Path(bundle_dir).resolve()
    return RepoEntry(
        base_iri=base_iri,
        title=bundle.meta.get("title") or base_iri,
        source_base=source_base or root.as_uri(),
        path=str(root),
        void=void,
        id_index=id_index,
    )
