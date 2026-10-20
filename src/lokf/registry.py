"""Cross-bundle federation: a registry of LOKF bundles (*meta-lokf*).

A registry (``lokf-registry.yaml``) maps each member bundle's ``base_iri`` to
where its exported artifacts and source documents live. The one load-bearing
operation is :meth:`Registry.owner` — longest-``base_iri``-prefix routing, the
exact inverse of :meth:`lokf.model.Bundle.iri` minting — so following an IRI
from one bundle into another is pure string math: no network, no shared
database. See SPEC §11.

This module holds the offline core (Phase 1): loading/saving the manifest,
building an entry from a local bundle or a released bundle archive, and
resolving an IRI to its owning bundle + Concept ID + source URL. It also
fetches each member's graph for the federated store (Phase 2, see
:meth:`lokf.store.GraphStore.from_registry`) and reports the relation
targets no member holds.
"""
from __future__ import annotations

import collections
import dataclasses
import hashlib
import http.client
import ipaddress
import pathlib
import re
import shutil
import socket
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from collections import Counter
from dataclasses import dataclass, field

import yaml

#: The ontology ``@vocab``. Never a repo ``base_iri`` — an IRI under it that no
#: (strictly longer) member owns is a vocabulary term, not a foreign concept.
VOCAB_NS = "https://w3id.org/lokf/"
REGISTRY_VERSION = "0.1"
DEFAULT_REGISTRY = "lokf-registry.yaml"
#: An entry of this type is a registry in turn (SPEC §11.2): its ``registry``
#: field locates that registry's manifest, which a walk of the tree follows.
CATALOG = "dcat:Catalog"
_CATALOG_TYPES = (CATALOG, "http://www.w3.org/ns/dcat#Catalog")
#: The most a sub-registry's manifest may be: it is a list of entries, not an archive.
MAX_MANIFEST_BYTES = 4 << 20
#: How many tiers below the top registry a walk follows, unless it sets ``max_depth``.
DEFAULT_MAX_DEPTH = 3
#: Ceiling on a bundle archive's size, downloaded and unpacked, so a hostile
#: zip or an endless response cannot fill the disk.
MAX_ARCHIVE_BYTES = 1 << 30
#: Ceiling on a bundle archive's entry count: a zip of empty files costs no
#: bytes but one inode, and time, apiece.
MAX_ARCHIVE_ENTRIES = 100_000
#: The longest a download may take in all; each read has its own shorter timeout.
DOWNLOAD_SECONDS = 600
_CHECKSUM = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{64})$")


@dataclass
class RepoEntry:
    """One member bundle. ``base_iri`` is its identity and routing key."""

    base_iri: str
    title: str = ""
    repo: str | None = None
    source_base: str = ""
    path: str | None = None
    distribution: dict = field(default_factory=dict)
    checksum: str | None = None  # "sha256:<hex>" of the archive it was registered from
    void: dict = field(default_factory=dict)
    id_index: dict = field(default_factory=dict)  # explicit-id IRI -> Concept ID
    sensitivity: str | None = None
    status: str = "ok"
    type: str | None = None  # CATALOG for a registry that is a member of this one
    registry: str | None = None  # a CATALOG entry's manifest, a URL or a path beside this one


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


def _source_url(
    entry: RepoEntry, concept_id: str | None, base: pathlib.Path | None = None
) -> str | None:
    """A concept's source-markdown URL: ``source_base``/``concept_id``.md, or
    without a ``source_base`` the file under the entry's local ``path``, read
    relative to *base* (the manifest's directory) when it is relative.

    Returns ``None`` when the entry has neither, or the IRI is the bundle's
    namespace root (empty Concept ID) — neither names a document.
    """
    if not concept_id:
        return None
    if entry.source_base:
        return entry.source_base.rstrip("/") + "/" + concept_id + ".md"
    if entry.path:
        root = pathlib.Path(entry.path)
        if not root.is_absolute() and base is not None:
            root = base / root
        return (root.resolve() / (concept_id + ".md")).as_uri()
    return None


@dataclass
class Registry:
    """A registry of LOKF bundles, loaded from ``lokf-registry.yaml``."""

    path: pathlib.Path
    id: str = ""
    title: str = ""
    publisher: dict = field(default_factory=dict)
    version: str = REGISTRY_VERSION
    repos: list[RepoEntry] = field(default_factory=list)
    max_depth: int | None = None  # tiers a walk of the tree follows, for a top registry
    #: What a walk of the tree left out by design, such as a registry deeper
    #: than ``max_depth`` (see :func:`load_tree`); not saved.
    notes: list[str] = field(default_factory=list)
    #: Sub-registries a walk could not read, each with its reason; not saved.
    skipped: list[str] = field(default_factory=list)

    # -- resolution ---------------------------------------------------------
    def _match(self, iri: str) -> tuple[RepoEntry | None, str | None, str | None]:
        """(entry, via, concept_id) for *iri*, or (None, None, None).

        Longest-``base_iri``-prefix wins; another member's ``id_index`` is
        only a *fallback* for an IRI that no base_iri prefixes (SPEC §11 rule
        1), so a stale index entry can never hijack an IRI a member owns by
        prefix. The owner's own ``id_index`` does name the concept, though: an
        explicit ``id`` under its base_iri that differs from base_iri + Concept
        ID would otherwise route to a document that does not exist.
        """
        best: RepoEntry | None = None
        for e in self.repos:
            if e.base_iri and iri.startswith(e.base_iri):
                if best is None or len(e.base_iri) > len(best.base_iri):
                    best = e
        if best is not None:
            if iri in best.id_index:
                return best, "id_index", best.id_index[iri]
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
            source_url=_source_url(entry, concept_id, self.path.parent if self.path else None)
            if entry else None,
            via=via,
        )

    # -- mutation -----------------------------------------------------------
    def add(self, entry: RepoEntry) -> bool:
        """Validate and append *entry*; return False when it is already there.

        A base_iri must be non-empty, end in a path separator (``/`` or ``#``)
        so prefix routing respects segment boundaries (``…/team/`` never
        captures ``…/team-archive/``), stay clear of the vocabulary namespace,
        and not nest with an existing member (that would make routing
        ambiguous). An entry for a registered base_iri is accepted, and not
        appended, when it describes the same release (see
        :func:`release_difference`), so the union of two registries that name
        one bundle can be built; at another release it raises ``ValueError``.
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
                differs = release_difference(e, entry)
                if differs:
                    raise ValueError(
                        f"base_iri already registered at another release: {b} "
                        f"({differs} differs)"
                    )
                return False
            if b.startswith(e.base_iri) or e.base_iri.startswith(b):
                raise ValueError(
                    f"base_iri {b!r} nests with registered {e.base_iri!r}; "
                    "base_iris must not be prefixes of one another"
                )
        # An explicit id may lie outside its own base_iri (SPEC §11.3 rule 1),
        # but never inside another member's namespace or the vocabulary's, in
        # either order of registration: prefix routing would win and the index
        # entry would never route, or it would claim a namespace it does not
        # own. Nor may two members index one id: which of them it routes to
        # would hang on the order they were registered in.
        for iri in entry.id_index:
            if iri.startswith(VOCAB_NS) and not iri.startswith(b):
                raise ValueError(f"explicit id {iri} lies in the vocabulary namespace")
            for e in self.repos:
                if iri.startswith(e.base_iri):
                    raise ValueError(
                        f"explicit id {iri} lies in registered {e.base_iri!r}"
                    )
                if iri in e.id_index:
                    raise ValueError(
                        f"explicit id {iri} is already indexed by registered {e.base_iri!r}"
                    )
        for e in self.repos:
            for iri in e.id_index:
                if iri.startswith(b):
                    raise ValueError(
                        f"base_iri {b!r} captures explicit id {iri} "
                        f"of registered {e.base_iri!r}"
                    )
        self.repos.append(entry)
        return True

    def to_dict(self) -> dict:
        """The manifest as a plain dict for YAML serialization."""
        d: dict = {"lokf_registry_version": self.version, "type": "dcat:Catalog"}
        if self.id:
            d["id"] = self.id
        if self.title:
            d["title"] = self.title
        if self.publisher:
            d["publisher"] = self.publisher
        if self.max_depth is not None:
            d["max_depth"] = self.max_depth
        d["repos"] = [_entry_dict(e) for e in self.repos]
        return d

    def located(self) -> "Registry":
        """A copy whose local locations are absolute, read against the
        manifest's directory: a relative ``path`` or ``distribution`` value
        names a file beside the manifest, wherever the process runs."""
        base = self.path.parent.resolve() if self.path else None
        return dataclasses.replace(self, repos=[_located(e, base) for e in self.repos])

    def save(self) -> None:
        """Write the manifest back to :attr:`path` (block-style YAML)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def _located(entry: RepoEntry, base: pathlib.Path | None) -> RepoEntry:
    """*entry* with its relative local locations made absolute against *base*."""
    located = dataclasses.replace(entry, distribution=dict(entry.distribution))
    if base is None:
        return located

    def local(value: str) -> str:
        if is_url(value) or value.startswith("file://") or pathlib.Path(value).is_absolute():
            return value
        return str((base / value).resolve())

    if located.path:
        located.path = local(located.path)
    for key, value in located.distribution.items():
        if isinstance(value, str) and value:
            located.distribution[key] = local(value)
    return located


#: The fields that say which release an entry describes, when no checksum does.
_RELEASE_FIELDS = ("repo", "source_base", "distribution", "id_index")


def release_difference(a: RepoEntry, b: RepoEntry) -> str | None:
    """What shows *a* and *b* describe different releases, or None.

    Two checksums decide it alone: the same digest is the same bytes, whatever
    either entry says about where they are. One checksum without the other
    cannot be compared, so it counts as a difference. Otherwise every release
    field must match. ``title``, ``path`` and ``status`` are a registry's own
    notes, and ``void`` is counted by whichever lokf registered the entry;
    none of them is the release, and none is compared.
    """
    if a.checksum and b.checksum:
        return None if a.checksum == b.checksum else "checksum"
    if a.checksum or b.checksum:
        return "checksum (one entry has one, the other none)"
    for name in _RELEASE_FIELDS:
        if getattr(a, name) != getattr(b, name):
            return name
    return None


def fill_locations(held: RepoEntry, new: RepoEntry) -> bool:
    """Copy into *held* the locations *new* knows and it lacks, or knows only
    as a local path; True if any.

    For one registrant adding a second location of a release it registered
    (the URL of a zip first added from disk, say). A walk of a registry tree
    never calls it: there a deeper registry could add an unchecked
    ``distribution.rdf`` to an entry a registry above it vouched for.
    """
    changed = False
    for name in ("repo", "source_base", "path"):
        if not getattr(held, name) and getattr(new, name):
            setattr(held, name, getattr(new, name))
            changed = True
    for key, value in new.distribution.items():
        current = held.distribution.get(key)
        # A published URL beats a local path for the same artifact.
        if current is None or (is_url(str(value)) and not is_url(str(current))):
            if current != value:
                held.distribution[key] = value
                changed = True
    return changed


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


def _entry_from(raw, where: str) -> RepoEntry:
    """A :class:`RepoEntry` from one manifest entry, checked field by field."""
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be a mapping, got {type(raw).__name__}")
    fields = {k: v for k, v in raw.items() if k in _ENTRY_FIELDS and v is not None}
    if not isinstance(fields.get("base_iri"), str) or not fields["base_iri"]:
        raise ValueError(f"{where} has no base_iri")
    for name, value in fields.items():
        kind = dict if isinstance(_ENTRY_DEFAULTS[name], dict) else str
        if not isinstance(value, kind):
            raise ValueError(f"{where}: {name} must be a {kind.__name__}, got {type(value).__name__}")
    if "checksum" in fields:
        m = _CHECKSUM.match(fields["checksum"].strip())
        if not m:
            raise ValueError(f"{where}: checksum must be sha256:<64 hex digits>")
        fields["checksum"] = "sha256:" + m.group(1).lower()
    return RepoEntry(**fields)


def load_registry(path: str | pathlib.Path) -> Registry:
    """Load ``lokf-registry.yaml`` with a plain YAML reader (no LinkML).

    Tolerant of a hand-edited manifest: a null ``repos:`` or null field values
    fall back to defaults rather than crashing a later lookup. A field of the
    wrong kind (a list where a string belongs, an entry without a
    ``base_iri``) is a ``ValueError`` naming the entry, and a checksum is
    normalised to ``sha256:`` and lowercase hex, so a hand-written one compares
    equal to the digest the toolkit computes.
    """
    p = pathlib.Path(path)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{p}: not valid YAML: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{p}: registry must be a YAML mapping, got {type(data).__name__}")
    entries = data.get("repos") or []
    if not isinstance(entries, list):
        raise ValueError(f"{p}: 'repos' must be a list")
    repos = [_entry_from(r, f"{p}: repos[{i}]") for i, r in enumerate(entries)]
    return Registry(
        path=p,
        id=data.get("id") or "",
        title=data.get("title") or "",
        publisher=data.get("publisher") or {},
        version=str(data.get("lokf_registry_version") or REGISTRY_VERSION),
        repos=repos,
        max_depth=_max_depth(data.get("max_depth"), p),
    )


def _max_depth(value, where) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{where}: max_depth must be a whole number of tiers, 0 or more")
    return value


def is_catalog(entry: RepoEntry) -> bool:
    """True for an entry that is a registry in turn: one that names its
    manifest in ``registry``, or is typed ``dcat:Catalog`` (CURIE or IRI)."""
    return bool(entry.registry) or entry.type in _CATALOG_TYPES


def has_bundle(entry: RepoEntry) -> bool:
    """True unless *entry* is a catalog with no bundle of its own: one that
    only reserves a namespace for the registry it names."""
    return not is_catalog(entry) or bool(entry.path or entry.distribution)


def _local_ref(value: str) -> pathlib.Path | None:
    """*value* as a local path when it names one (a ``file://`` URI or an
    absolute path), else None (a URL, or a path relative to its manifest)."""
    if value.lower().startswith("file://"):
        return pathlib.Path(urllib.request.url2pathname(urllib.parse.urlsplit(value).path))
    path = pathlib.Path(value)
    return path if path.is_absolute() else None


def _locate(ref: str, parent: str) -> str | None:
    """*ref*, a sub-registry's manifest, resolved against its parent's location.

    A manifest read from a URL may only point at URLs: a local path in it
    would have this machine's files read on someone else's word, so None.
    """
    if is_url(ref):
        return ref
    local = _local_ref(ref)
    if is_url(parent):
        return None if local is not None else urllib.parse.urljoin(parent, ref)
    if local is not None:
        return str(local.resolve())
    return str((pathlib.Path(parent).parent / ref).resolve())


def _as_listed(entry: RepoEntry, where: str) -> RepoEntry:
    """*entry*'s locations as the manifest at *where* gives them.

    Relative ones are read beside that manifest. From a manifest read at a
    URL, a relative location is a URL beside it, and a local path or
    ``file://`` location is dropped, as :func:`_locate` refuses one.
    """
    if not is_url(where):
        return _located(entry, pathlib.Path(where).parent)
    listed = dataclasses.replace(entry, path=None, distribution={})
    for key, value in entry.distribution.items():
        if isinstance(value, str) and value and _local_ref(value) is None:
            listed.distribution[key] = value if is_url(value) else urllib.parse.urljoin(where, value)
    return listed


def load_tree(top: str | pathlib.Path | Registry, max_depth: int | None = None) -> Registry:
    """A registry and every registry below it, as one flat registry.

    *top* is a manifest path or an already loaded :class:`Registry`. A catalog
    entry (:func:`is_catalog`) is followed to the manifest its ``registry``
    field names, resolved against the manifest that lists it, to *max_depth*
    tiers below the top (else the top's ``max_depth``, else
    :data:`DEFAULT_MAX_DEPTH`); a deeper one is left out with a note. Every
    entry's relative locations are read beside the manifest that lists it.

    The walk goes tier by tier, so where registries name one bundle the entry
    nearest the top is the one kept; a registry two others name is read
    once. A catalog entry joins too, so its namespace stays reserved and a
    bundle of its own (``path`` or a ``distribution``) loads. A bundle named
    at two releases raises ``ValueError``, since a named graph holds one
    release, and so does a registry that names itself or one above it. A
    sub-registry that cannot be read is left out and listed in ``skipped``.
    """
    if isinstance(top, Registry):
        root, top_path = top, (top.path.resolve() if top.path else pathlib.Path.cwd() / DEFAULT_REGISTRY)
    else:
        top_path = pathlib.Path(top).resolve()
        root = load_registry(top_path)
    limit = DEFAULT_MAX_DEPTH
    for value in (max_depth, root.max_depth):
        if value is not None:
            limit = _max_depth(value, top_path)
            break
    flat = Registry(path=root.path, id=root.id, title=root.title, publisher=root.publisher,
                    version=root.version, max_depth=root.max_depth)
    origin: dict[str, str] = {}
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="lokf-registry-tree-"))

    def add(entry: RepoEntry, where: str) -> None:
        try:
            if flat.add(entry):
                origin[entry.base_iri] = where
        except ValueError as exc:
            first = origin.get(entry.base_iri)
            also = f"; first named in {first}" if first and first != where else ""
            raise ValueError(f"{where}: {exc}{also}") from None

    start = str(top_path)
    queue = collections.deque([(root, start, 0, frozenset({start} | ({root.id} if root.id else set())))])
    read = {start}
    try:
        while queue:
            reg, where, depth, above = queue.popleft()
            for e in reg.repos:
                e = _as_listed(e, where)
                add(e, where)
                if not is_catalog(e):
                    continue
                if not e.registry:
                    raise ValueError(f"{where}: catalog entry {e.base_iri} names no registry")
                loc = _locate(e.registry, where)
                if loc is None:
                    flat.skipped.append(f"{e.registry}: a local path in {where}, a manifest read from a URL")
                    continue
                if loc in above:
                    raise ValueError(f"{where}: {e.base_iri} names a registry above it, {loc}")
                if loc in read:
                    continue
                if depth + 1 > limit:
                    flat.notes.append(f"not followed: {loc}, deeper than max_depth {limit}")
                    continue
                read.add(loc)
                try:
                    dest = tmp / f"{len(read)}.yaml"
                    sub = load_registry(_fetch(loc, dest, max_bytes=MAX_MANIFEST_BYTES))
                except (ValueError, OSError) as exc:
                    flat.skipped.append(f"{loc}: {exc}")
                    continue
                if sub.id and sub.id in above:
                    raise ValueError(
                        f"{loc} has the id {sub.id} of a registry above it: a cycle, or a "
                        "manifest copied from its parent that needs an id of its own"
                    )
                queue.append((sub, loc, depth + 1, above | {loc} | ({sub.id} if sub.id else set())))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return flat


def entry_for_bundle(
    bundle_dir: str | pathlib.Path,
    source_base: str | None = None,
    allow_foreign_ids: bool = False,
) -> RepoEntry:
    """Build a :class:`RepoEntry` from a local bundle directory.

    Derives ``base_iri``/``title``/``publisher`` from the bundle's ``index.md``,
    computes a VoID planning index (triple + per-type counts), and harvests an
    ``id_index`` of explicit-``id`` IRIs that diverge from ``base_iri`` +
    Concept ID (so they still route). ``path`` records the directory as an
    absolute path; ``lokf registry add`` writes it relative to the manifest.

    Raises ``ValueError`` if the bundle has no ``base_iri``, or if an explicit
    ``id`` lies outside ``base_iri`` and *allow_foreign_ids* is false: a bundle
    must declare that it mints IRIs in a namespace it does not route by prefix
    (SPEC §11.3 rule 3).
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

    foreign = sorted(iri for iri in id_index if not iri.startswith(base_iri))
    if foreign and not allow_foreign_ids:
        raise ValueError(
            f"{len(foreign)} explicit id(s) lie outside base_iri {base_iri}, "
            f"first {foreign[0]}; allow foreign ids to index them"
        )

    part = Counter(c.type for c in bundle.concepts)
    void = {"triples": len(bundle.graph()), "class_partition": dict(part)}

    root = pathlib.Path(bundle_dir).resolve()
    return RepoEntry(
        base_iri=base_iri,
        title=bundle.meta.get("title") or base_iri,
        source_base=source_base or "",
        path=str(root),
        void=void,
        id_index=id_index,
    )


def is_url(source: str) -> bool:
    """True when *source* names an archive to download rather than a local path."""
    return source[:8].lower().startswith(("https://", "http://"))


def _is_local_host(host: str | None) -> bool:
    """True when *host* resolves to a loopback, private, link-local or
    otherwise non-public address."""
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False  # unresolvable: the request fails on its own
    for info in infos:
        ip = ipaddress.ip_address(str(info[4][0]).split("%", 1)[0])
        if not ip.is_global:
            return True
    return False


class _Redirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to http(s), never from https down to http, and
    never into the local network unless the first URL pointed there: a
    release URL may move to a CDN, not to a service beside the registrant."""

    def __init__(self, local_ok: bool):
        self.local_ok = local_ok

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if new.scheme not in ("http", "https") or (old.scheme == "https" and new.scheme == "http"):
            raise urllib.error.URLError(f"refused redirect from {req.full_url} to {newurl}")
        if not self.local_ok and _is_local_host(new.hostname):
            raise urllib.error.URLError(f"refused redirect into the local network: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url: str, timeout: float = 60):
    """Open an http(s) *url*, following only the redirects :class:`_Redirects`
    allows. Raises ``OSError`` for anything that goes wrong on the wire and
    ``ValueError`` for a URL that is not http(s)."""
    first = urllib.parse.urlsplit(url)
    if first.scheme.lower() not in ("http", "https"):
        raise ValueError(f"not an http(s) URL: {url}")
    opener = urllib.request.build_opener(_Redirects(local_ok=_is_local_host(first.hostname)))
    try:
        return opener.open(url, timeout=timeout)
    except http.client.HTTPException as exc:  # InvalidURL and friends are not OSErrors
        raise OSError(f"{url}: {exc}") from exc


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _download(url: str, dest: pathlib.Path, max_bytes: int = MAX_ARCHIVE_BYTES) -> None:
    """Stream *url* into *dest*, refusing more than *max_bytes* or a transfer
    longer than :data:`DOWNLOAD_SECONDS`. A failed download leaves no file."""
    deadline = time.monotonic() + DOWNLOAD_SECONDS
    try:
        with open_url(url) as resp, dest.open("wb") as out:
            total = 0
            for chunk in iter(lambda: resp.read(1 << 20), b""):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"{url} is larger than {max_bytes} bytes")
                if time.monotonic() > deadline:
                    raise OSError(f"{url} took longer than {DOWNLOAD_SECONDS} seconds")
                out.write(chunk)
    except http.client.HTTPException as exc:  # a truncated chunked response
        dest.unlink(missing_ok=True)
        raise OSError(f"{url}: {exc}") from exc
    except BaseException:
        dest.unlink(missing_ok=True)
        raise


def _fetch(source: str, dest: pathlib.Path, max_bytes: int = MAX_ARCHIVE_BYTES) -> pathlib.Path:
    """*source* as a local file: downloaded into *dest* when it is a URL,
    else the path itself (a ``file://`` URI is accepted too)."""
    if is_url(source):
        _download(source, dest, max_bytes=max_bytes)
        return dest
    if source.startswith("file://"):
        return pathlib.Path(urllib.request.url2pathname(source[len("file://"):]))
    return pathlib.Path(source)


def _unpack(archive: pathlib.Path, dest: pathlib.Path, label: str | None = None) -> pathlib.Path:
    """Unpack a bundle zip into *dest* and return the bundle's root directory.

    The root is *dest* itself when the zip carries ``index.md`` at its top, or
    the one top-level directory that does (a KTL release zip's ``knowledge/``).
    Members with absolute or ``..`` paths, and zips that unpack to more than
    :data:`MAX_ARCHIVE_BYTES` or hold more than :data:`MAX_ARCHIVE_ENTRIES`
    entries, are refused before anything is written. *label* names the
    archive in errors (its URL, say, rather than a temporary file); a zip
    that is corrupt, encrypted or compressed in a way zipfile cannot read is
    a ``ValueError`` too.
    """
    name = label or archive.name
    if not zipfile.is_zipfile(archive):
        raise ValueError(f"{name} is not a zip archive")
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise ValueError(
                    f"{name} holds {len(infos)} entries, more than {MAX_ARCHIVE_ENTRIES}"
                )
            for info in infos:
                parts = pathlib.PurePosixPath(info.filename).parts
                if info.filename.startswith(("/", "\\")) or ".." in parts:
                    raise ValueError(f"{name}: unsafe member path {info.filename!r}")
            if sum(i.file_size for i in infos) > MAX_ARCHIVE_BYTES:
                raise ValueError(f"{name} unpacks to more than {MAX_ARCHIVE_BYTES} bytes")
            zf.extractall(dest)
    except (zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError, EOFError) as exc:
        raise ValueError(f"{name} cannot be unpacked: {exc}") from exc
    if (dest / "index.md").is_file():
        return dest
    roots = [d for d in dest.iterdir() if d.is_dir() and (d / "index.md").is_file()]
    if len(roots) != 1:
        raise ValueError(
            f"{name}: expected index.md at the top or in one top-level "
            f"directory, found {len(roots)}"
        )
    return roots[0]


def entry_for_archive(
    source: str | pathlib.Path,
    source_base: str | None = None,
    checksum: str | None = None,
    allow_foreign_ids: bool = False,
    archive_url: str | None = None,
) -> RepoEntry:
    """Build a :class:`RepoEntry` from a released bundle zip, local or at a URL.

    The zip is unpacked to a temporary directory and registered from there, so
    the entry never records a ``path``. Its digest goes in ``checksum``; when
    *checksum* is given (``sha256:<hex>`` or bare hex) a mismatch is refused.
    ``distribution.archive`` records where the zip is published: *archive_url*
    when given (a CI job registers the local copy of a zip it is about to
    publish), else the URL it was read from, else its absolute local path,
    which ``lokf registry add`` writes relative to the manifest. Without
    *source_base* the entry has no source URL, as an unpacked copy is gone.
    """
    if archive_url is not None and not is_url(archive_url):
        raise ValueError(f"archive_url must be an http(s) URL, got {archive_url!r}")
    expected = None
    if checksum:
        m = _CHECKSUM.match(checksum.strip())
        if not m:
            raise ValueError(f"checksum must be sha256:<64 hex digits>, got {checksum!r}")
        expected = "sha256:" + m.group(1).lower()

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="lokf-registry-"))
    try:
        archive = _fetch(str(source), tmp / "bundle.zip")
        digest = _sha256(archive)
        if expected and digest != expected:
            raise ValueError(f"checksum mismatch: expected {expected}, got {digest}")
        root = _unpack(archive, tmp / "unpacked", label=str(source))
        entry = entry_for_bundle(
            root, source_base=source_base, allow_foreign_ids=allow_foreign_ids
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    entry.path = None
    entry.source_base = source_base or ""
    entry.checksum = digest
    where = str(source) if is_url(str(source)) else str(archive.resolve())
    entry.distribution = {"archive": archive_url or where}
    return entry


def member_ntriples(entry: RepoEntry) -> str:
    """A member's graph as N-Triples, offline first (SPEC §11.4).

    Tries the local checkout in ``path``, projected under the domain schema
    its project declares; then ``distribution.rdf`` (a ``graph.nt`` from
    ``lokf export``); then ``distribution.archive``, checked against
    ``checksum`` and projected under core LOKF. Only the archive is checked:
    a ``distribution.rdf`` is trusted as the manifest lists it. Relative
    locations are read as :meth:`Registry.located` leaves them. Raises
    ``ValueError`` when the entry names none of them, or ``OSError`` when the
    one it names is unreachable.
    """
    from lokf import rdf
    from lokf.schema import domain_schema

    if entry.path and pathlib.Path(entry.path).is_dir():
        return rdf.serialize(entry.path, "nt", schema=domain_schema(None, entry.path))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="lokf-registry-"))
    try:
        if entry.distribution.get("rdf"):
            nt = _fetch(str(entry.distribution["rdf"]), tmp / "graph.nt")
            return nt.read_text(encoding="utf-8")
        if entry.distribution.get("archive"):
            archive = _fetch(str(entry.distribution["archive"]), tmp / "bundle.zip")
            if entry.checksum and _sha256(archive) != entry.checksum:
                raise ValueError(f"archive does not match checksum {entry.checksum}")
            root = _unpack(archive, tmp / "unpacked", label=str(entry.distribution["archive"]))
            return rdf.serialize(root, "nt")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    raise ValueError("no local path, distribution.rdf or distribution.archive to load")


@dataclass
class Unresolved:
    """A typed-relation target, asserted in *graph*, that the registry cannot
    follow: no member owns it (``unowned``), or its owner holds no such
    concept (``missing``)."""

    graph: str
    predicate: str
    target: str
    kind: str


def unresolved_targets(registry: Registry, store) -> list[Unresolved]:
    """Typed-relation targets outside the asserting member that do not resolve.

    *store* is a :class:`lokf.store.GraphStore` built with
    :meth:`~lokf.store.GraphStore.from_registry`. This is ``--check-refs``
    across bundles: a target under the asserting member's own ``base_iri`` is
    that bundle's own check, and is skipped here. So is a term of the LOKF
    vocabulary no member owns, which is not a concept, and a target whose
    owner failed to load, which cannot be checked (the load error says so).
    """
    import pyoxigraph as ox

    from lokf.schema import vocabulary

    vocab = vocabulary()
    predicates = {r.uri for r in vocab.relation_slots.values()}
    predicates |= {r.uri for r in vocab.relation_types.values()}
    predicates.add("http://www.w3.org/1999/02/22-rdf-syntax-ns#object")  # reified target

    out: set[tuple[str, str, str, str]] = set()
    for pred in sorted(predicates):
        for q in store.store.quads_for_pattern(None, ox.NamedNode(pred), None, None):
            if not isinstance(q.object, ox.NamedNode) or not isinstance(q.graph_name, ox.NamedNode):
                continue
            graph, target = q.graph_name.value, q.object.value
            if target.startswith(graph):
                continue
            owner = registry.owner(target)
            if owner is None:
                if not target.startswith(VOCAB_NS):
                    out.add((graph, pred, target, "unowned"))
            elif owner.base_iri in store.load_errors:
                continue
            elif not any(
                store.store.quads_for_pattern(
                    q.object, None, None, ox.NamedNode(owner.base_iri)
                )
            ):
                out.add((graph, pred, target, "missing"))
    return [Unresolved(*row) for row in sorted(out)]
