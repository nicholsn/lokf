"""Capture immutable bundle and federation reads in an operator-owned SQLite file."""
from __future__ import annotations

from collections import deque
from contextlib import closing, contextmanager
from functools import lru_cache, wraps
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import sqlite3
import stat
from tempfile import TemporaryDirectory
from threading import Lock

import pyoxigraph as ox
from typing_extensions import TypedDict

from lokf import rdf
from lokf.model import RESERVED, _load_bundle_files, _markdown_files
from lokf.registry import _sha256, has_bundle, load_tree
from lokf.registry_mcp import DOCUMENT_MAX_BYTES, ROWS_MAX, query_registry
from lokf.schema import domain_schema, schema_context, schema_path, vocabulary
from lokf.schema_sources import capture
from lokf.store import GraphStore

_APPLICATION_ID = 0x4C4F4B46  # LOKF
_FORMAT = "lokf-read-snapshot-v1"
_TABLES = (
    "CREATE TABLE head (id INTEGER PRIMARY KEY CHECK (id = 1), scope TEXT NOT NULL, revision TEXT NOT NULL)",
    "CREATE TABLE snapshots (revision TEXT PRIMARY KEY, manifest TEXT NOT NULL)",
    "CREATE TABLE members (revision TEXT PRIMARY KEY, schema_info TEXT NOT NULL, vocabulary TEXT NOT NULL,"
    " prefixes TEXT NOT NULL, graph BLOB NOT NULL)",
    "CREATE TABLE blobs (digest TEXT PRIMARY KEY, markdown BLOB NOT NULL) WITHOUT ROWID",
    "CREATE TABLE documents (member TEXT NOT NULL, path TEXT NOT NULL, iri TEXT, digest TEXT NOT NULL,"
    " PRIMARY KEY (member, path)) WITHOUT ROWID",
    "CREATE INDEX document_iri ON documents (member, iri)",
)


class SnapshotLookupError(ValueError):
    """A requested revision, member or document cannot be served."""


class MemberRevision(TypedDict):
    base_iri: str
    revision: str
    schema_revision: str
    profile: dict[str, str]


class SnapshotInfo(TypedDict):
    snapshot: str
    format: str
    kind: str
    registry_id: str | None
    members: list[MemberRevision]


class DocumentRead(TypedDict):
    snapshot: str
    member_revision: str
    path: str
    sha256: str
    markdown: str


class VocabularyRead(TypedDict):
    snapshot: str
    member_revision: str
    schema_metadata: dict
    vocabulary: dict


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(data):
    return "sha256:" + sha256(data).hexdigest()


def _check_format(db):
    if (db.execute("PRAGMA application_id").fetchone()[0] != _APPLICATION_ID
            or db.execute("PRAGMA user_version").fetchone()[0] != 1):
        raise ValueError("Unrecognized LOKF snapshot store or format")


def _read(root, path, store_stat):
    target = path.resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError(f"Cannot capture Markdown outside the bundle or from a special file: {path}")
    with target.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if os.path.samestat(info, store_stat):
            raise ValueError(f"Snapshot store overlaps a bundle input: {path}")
        if not stat.S_ISREG(info.st_mode) or info.st_size > DOCUMENT_MAX_BYTES:
            raise ValueError(f"Expected a regular Markdown file of at most {DOCUMENT_MAX_BYTES} bytes: {path}")
        data = stream.read(info.st_size + 1)
    if len(data) != info.st_size:
        raise ValueError(f"Markdown changed during capture: {path}. Retry capture.")
    return data


def _graph_bytes(graph):
    from rdflib import BNode

    # Ground RDF already has stable labels. The capture parser checks these bytes before publication.
    if any(isinstance(term, BNode) for triple in graph for term in triple):
        graph = rdf.relabel_bnodes(graph)
    return rdf._sorted_nt(graph).encode()


class _SchemaProjection:
    """Schema-derived bytes shared by members with identical captured inputs."""

    def __init__(self, inputs, domain):
        schema = inputs.metadata()
        self.revision = schema["revision"]
        self.metadata = _json(schema)
        vocab = vocabulary(inputs)
        self.vocabulary = _json(vocab.manifest())
        self.vocabulary_digest = _digest(self.vocabulary.encode())
        self.prefixes = vocab.prefixes
        self.encoded_prefixes = _json(self.prefixes)
        self.versions = {name: version(name) for name in ("lokf", "rdflib", "pyoxigraph")}
        if domain:
            self.versions["linkml"] = version("linkml")


def _capture_member(db, root, store_stat, project_schema, expected_base=None, *, checkout=True):
    root = root.resolve(strict=True)
    files = _markdown_files(root)
    index = root / "index.md"
    if index not in files:
        raise ValueError(f"No index.md in {root}")
    paths = {}

    def text(path):
        raw = _read(root, path, store_stat)
        paths[path.relative_to(root).as_posix()] = _digest(raw)
        # Match the model's universal-newline reader. Retain the exact bytes on verification.
        return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")

    for p in files:
        if p.name in RESERVED and p != index:
            text(p)  # Reserved pages must also decode successfully.
    bundle = _load_bundle_files(root, files, True, read=text)
    base = bundle.base_iri
    if not base or (expected_base is not None and base != expected_base):
        raise ValueError(f"Bundle base_iri {base!r} missing or disagrees with registry {expected_base!r}")
    ox.NamedNode(base)  # a named graph needs an absolute IRI
    selected = domain_schema(None, root) if checkout else None
    inputs = capture(schema_path(selected))  # a live schema import cannot be pinned
    context = schema_context(inputs if selected else None)
    schema = project_schema(inputs, bool(selected))
    profile = {"format": _FORMAT, "validation": "not_run", "context": _digest(_json(context).encode()),
               **schema.versions}
    nt = _graph_bytes(bundle.graph(context=context, schema=inputs))
    # RDFLib can serialize IRIs that the query engine refuses. Check before publishing the head.
    try:
        deque(ox.parse(nt, format=ox.RdfFormat.N_TRIPLES), maxlen=0)
    except SyntaxError as exc:
        raise ValueError(f"Bundle RDF cannot be queried: {exc}") from exc
    identity = {"base_iri": base, "documents": paths, "schema": schema.revision, "profile": profile,
                "graph": _digest(nt), "vocabulary": schema.vocabulary_digest,
                "prefixes": schema.prefixes}
    revision = _digest(_json(identity).encode())
    iris = {c.path: bundle.iri(c) for c in bundle.concepts}
    iris[index] = base
    changed = f"Bundle or schema changed during capture: {root}. Retry capture."
    for name, digest in paths.items():
        path = root / name
        raw = _read(root, path, store_stat)
        if _digest(raw) != digest:
            raise ValueError(changed)
        # Check the retained bytes in SQLite before building a replacement BLOB.
        if not db.execute("SELECT 1 FROM blobs WHERE digest=? AND markdown=?", (digest, raw)).fetchone():
            db.execute("INSERT OR REPLACE INTO blobs VALUES (?, ?)", (digest, raw))
        db.execute("INSERT INTO documents VALUES (?, ?, ?, ?) ON CONFLICT(member, path) DO UPDATE SET"
                   " iri=excluded.iri, digest=excluded.digest WHERE iri IS NOT excluded.iri OR digest != excluded.digest",
                   (revision, name, iris.get(path), digest))
    if (files != _markdown_files(root) or (checkout and selected != domain_schema(None, root))
            or not inputs.unchanged()):
        raise ValueError(changed)
    member_row = (revision, schema.metadata, schema.vocabulary, schema.encoded_prefixes, nt)
    if not db.execute("SELECT 1 FROM members WHERE revision=? AND schema_info=? AND vocabulary=?"
                      " AND prefixes=? AND graph=?", member_row).fetchone():
        db.execute("INSERT OR REPLACE INTO members VALUES (?, ?, ?, ?, ?)", member_row)
    # Preserve authored-ID lookups. Add the actual JSON-LD subjects to the derived index,
    # including on recapture of an existing v1 member.
    from rdflib.plugins.shared.jsonld.context import Context

    identifiers = Context(context, base=base)
    for concept in bundle.concepts:
        authored = iris[concept.path]
        subject = identifiers.resolve(authored)
        if subject and subject != authored:
            db.execute("INSERT OR IGNORE INTO document_aliases VALUES (?, ?, ?)",
                       (revision, subject, concept.path.relative_to(root).as_posix()))
    return {"base_iri": base, "revision": revision, "schema_revision": schema.revision, "profile": profile}


@contextmanager
def _member_root(entry):
    """A checkout, or one verified copy of a checksum-pinned release archive."""
    from lokf.registry import MAX_ARCHIVE_BYTES, _fetch, _unpack

    if entry.path and Path(entry.path).is_dir():
        yield Path(entry.path), True
        return
    archive = entry.distribution.get("archive")
    if not archive or not entry.checksum:
        raise ValueError("a local checkout or checksum-pinned bundle archive is required")
    with TemporaryDirectory(prefix="lokf-snapshot-") as tmp:
        dest = Path(tmp) / "member.zip"
        fetched = _fetch(str(archive), dest, max_bytes=MAX_ARCHIVE_BYTES)
        if fetched == dest:
            checksum = _sha256(dest)
        else:
            # Stage and hash the same bytes, even if the local release is being replaced.
            digest = sha256()
            if not fetched.is_file():
                raise ValueError(f"Expected a regular bundle archive: {archive}")
            with fetched.open("rb") as source, dest.open("wb") as out:
                size_error = f"{archive} is larger than {MAX_ARCHIVE_BYTES} bytes"
                if os.fstat(source.fileno()).st_size > MAX_ARCHIVE_BYTES:
                    raise ValueError(size_error)
                total = 0
                for chunk in iter(lambda: source.read(1 << 20), b""):
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise ValueError(size_error)
                    digest.update(chunk)
                    out.write(chunk)
            checksum = "sha256:" + digest.hexdigest()
        if checksum != entry.checksum:
            raise ValueError("archive checksum mismatch")
        yield _unpack(dest, Path(tmp) / "bundle", label=str(archive)), False


@contextmanager
def _writer(store, scope):
    """Serialize captures, including first-time initialization and scope binding."""
    try:
        fd = os.open(store, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(fd)
    with closing(sqlite3.connect(store, timeout=30)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        empty = db.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone() is None
        if empty and db.execute("PRAGMA application_id").fetchone()[0] == 0:
            for statement in _TABLES:
                db.execute(statement)
            db.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
            db.execute("PRAGMA user_version = 1")
        _check_format(db)
        head = db.execute("SELECT scope FROM head").fetchone()
        if head and head[0] != scope:
            raise ValueError("This store belongs to another source or clearance scope")
        db.execute("CREATE TABLE IF NOT EXISTS document_aliases (member TEXT, iri TEXT, path TEXT,"
                   " PRIMARY KEY (member, iri, path)) WITHOUT ROWID")
        yield db


def _registry_inputs(source, store, cleared):
    registry = load_tree(source, cleared_members=cleared).located()
    existing = store.exists()
    for path, _ in registry._manifest_inputs.values():
        if path == store or (existing and path.exists() and path.samefile(store)):
            raise ValueError(f"Snapshot store overlaps a registry manifest: {path}")
    if registry.skipped or registry.notes:
        raise ValueError("Registry member unavailable: " + "; ".join(registry.skipped + registry.notes))
    return registry


def capture_snapshot(source: Path, store: Path, *, cleared_members=()) -> SnapshotInfo:
    """Atomically retain one local bundle or registry and advance this store's head.

    The operator owns the store and fixes its source and clearance on first capture.
    Unavailable inputs abort the entire capture. No authored files are changed.
    """
    source = Path(source).resolve(strict=True)
    store = Path(store).resolve()
    kind = "bundle" if source.is_dir() else "registry"
    cleared = sorted(set(cleared_members))
    scope = _json([str(source), kind, cleared])
    if not source.is_dir() and not source.is_file():
        raise ValueError("Capture source must be a bundle directory or a regular registry manifest")
    if store.exists() and source.samefile(store):
        raise ValueError("Snapshot store overlaps the capture source")
    registry = None
    if not store.exists():
        # Creating SQLite must not create one of the inputs we are about to read.
        if kind == "registry":
            registry = _registry_inputs(source, store, cleared)
        if store.match("*.md"):
            roots = [source] if registry is None else [Path(e.path) for e in registry.repos if e.path]
            if any(store.is_relative_to(root.resolve()) for root in roots):
                raise ValueError("Snapshot store overlaps the bundle's Markdown input")
    with _writer(store, scope) as db:
        store_stat = store.stat()
        project_schema = lru_cache(maxsize=1)(_SchemaProjection)
        if kind == "bundle":
            members = [_capture_member(db, source, store_stat, project_schema)]
            registry_id = None
        else:
            # If another writer initialized the store in the meantime, select under its lock.
            if registry is None or db.execute("SELECT 1 FROM head").fetchone():
                registry = _registry_inputs(source, store, cleared)
            registry_id = registry.id or None
            if registry_id is not None and not isinstance(registry_id, str):
                raise ValueError("Registry id must be a string")
            members = []
            for entry in registry.repos:
                if not has_bundle(entry):
                    continue
                if (entry.sensitivity or "").strip().lower() not in ("", "public") and entry.base_iri not in cleared:
                    raise ValueError(f"Member unavailable: {entry.base_iri} requires explicit clearance")
                try:
                    with _member_root(entry) as (root, checkout):
                        members.append(_capture_member(db, root, store_stat, project_schema, entry.base_iri,
                                                       checkout=checkout))
                except Exception as exc:
                    raise ValueError(f"Member unavailable: {entry.base_iri}: {exc}") from exc
            for locator, (target, digest) in registry._manifest_inputs.items():
                if locator.resolve() != target or not target.is_file() or _sha256(target) != digest:
                    raise ValueError(f"Registry changed during capture: {locator}. Retry capture.")
        manifest = {"format": _FORMAT, "kind": kind, "registry_id": registry_id,
                    "members": sorted(members, key=lambda m: m["base_iri"])}
        encoded = _json(manifest)
        revision = _digest(encoded.encode())
        db.execute("INSERT INTO snapshots VALUES (?, ?) ON CONFLICT(revision) DO UPDATE SET manifest=excluded.manifest"
                   " WHERE manifest != excluded.manifest", (revision, encoded))
        db.execute("INSERT OR REPLACE INTO head VALUES (1, ?, ?)", (scope, revision))
    return {"snapshot": revision, **manifest}


class SnapshotReader:
    """Read one captured revision per call. Only the capture command opens the store for writing."""

    def __init__(self, store: Path):
        self._uri = Path(store).resolve().as_uri() + "?mode=ro"
        with self._connection() as db:
            _check_format(db)
        self._member_revisions = lru_cache(maxsize=1)(self._index_members)
        self._graph_row = None
        self._graph = None
        self._graph_lock = Lock()

    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(self._uri, uri=True, timeout=30)) as db:
            db.execute("BEGIN")  # Head, manifest and member data belong to the same read transaction.
            yield db

    @staticmethod
    def _snapshot_row(db, snapshot):
        if snapshot is None:
            row = db.execute("SELECT revision, manifest FROM snapshots JOIN head USING (revision)").fetchone()
        else:
            row = db.execute("SELECT revision, manifest FROM snapshots WHERE revision=?", (snapshot,)).fetchone()
        if row is None:
            raise SnapshotLookupError(f"Snapshot unavailable: {snapshot!r}")
        return row

    @staticmethod
    def _manifest(row):
        revision, encoded = row
        if _digest(encoded.encode()) != revision:
            raise SnapshotLookupError(f"Snapshot manifest digest mismatch: {revision}")
        return {"snapshot": revision, **json.loads(encoded)}

    def get_snapshot(self, snapshot: str | None = None) -> SnapshotInfo:
        """Resolve the current head or a specific snapshot to its member and schema revisions."""
        with self._connection() as db:
            return self._manifest(self._snapshot_row(db, snapshot))

    @staticmethod
    def _index_members(row):
        manifest = SnapshotReader._manifest(row)
        return {m["base_iri"]: m["revision"] for m in manifest["members"]}

    def _select(self, db, snapshot, base):
        # Include the stored manifest text in the key so changed bytes are always verified.
        row = self._snapshot_row(db, snapshot)
        members = self._member_revisions(row)
        if base is None and len(members) == 1:
            return row[0], next(iter(members.values()))
        if base in members:
            return row[0], members[base]
        raise SnapshotLookupError(f"Member unavailable in this snapshot: {base!r}; select a base_iri from get_snapshot")

    def read_document(self, path: str | None = None, member: str | None = None,
                      snapshot: str | None = None, iri: str | None = None) -> DocumentRead:
        """Read captured Markdown by bundle-relative path or graph IRI. Select a federation member by base IRI."""
        if (path is None) == (iri is None):
            raise SnapshotLookupError("Specify either a document path or an IRI")
        with self._connection() as db:
            revision, key = self._select(db, snapshot, member)
            if iri is not None:
                lookup = "SELECT path FROM documents WHERE member=? AND iri=?"
                params = (key, iri)
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='document_aliases'").fetchone():
                    lookup += " UNION ALL SELECT path FROM document_aliases WHERE member=? AND iri=?"
                    params += (key, iri)
                matches = db.execute(lookup + " LIMIT 2", params).fetchall()
                if len(matches) > 1:
                    raise SnapshotLookupError(f"Multiple documents declare {iri!r}; select a document path")
                path = matches[0][0] if matches else None
            row = db.execute("SELECT path, digest, markdown FROM documents JOIN blobs USING (digest) "
                             "WHERE member=? AND path=?", (key, path)).fetchone()
        if row is None:
            raise SnapshotLookupError(f"Document unavailable in this snapshot: {iri or path!r}")
        name, digest, markdown = row
        if _digest(markdown) != digest:
            raise SnapshotLookupError(f"Stored Markdown digest mismatch: {name}")
        return {"snapshot": revision, "member_revision": key, "path": name,
                "sha256": digest, "markdown": markdown.decode("utf-8")}

    def get_vocabulary(self, member: str | None = None, snapshot: str | None = None) -> VocabularyRead:
        """Read the retained schema metadata and vocabulary manifest of one member."""
        with self._connection() as db:
            revision, key = self._select(db, snapshot, member)
            row = db.execute("SELECT schema_info, vocabulary FROM members WHERE revision=?",
                             (key,)).fetchone()
        if row is None:
            raise SnapshotLookupError(f"Member revision unavailable: {key}")
        schema, vocab = row
        return {"snapshot": revision, "member_revision": key,
                "schema_metadata": json.loads(schema), "vocabulary": json.loads(vocab)}

    @staticmethod
    def _load_graph(db, manifest):
        cache = ox.Store()
        namespaces = {}
        for member in manifest["members"]:
            row = db.execute("SELECT graph, prefixes FROM members WHERE revision=?",
                             (member["revision"],)).fetchone()
            if row is None:
                raise SnapshotLookupError(f"Member revision unavailable: {member['revision']}")
            nt, prefixes = row
            graph = ox.NamedNode(member["base_iri"])
            cache.add_graph(graph)  # Empty bundles also own a named graph.
            try:
                # Capture already canonicalized these labels. Scope them once per member.
                triples = ox.parse(nt, format=ox.RdfFormat.N_TRIPLES)
                cache.extend(GraphStore._scoped_quads(graph, triples))
            except SyntaxError as exc:
                raise SnapshotLookupError(f"Member RDF unavailable: {member['base_iri']}: {exc}") from exc
            for name, uri in json.loads(prefixes).items():
                namespaces.setdefault(name, set()).add(uri)
        return GraphStore(cache, union=True, prefixes={name: next(iter(uris)) for name, uris in namespaces.items()
                                                      if len(uris) == 1})

    def federated_sparql(self, query: str, snapshot: str | None = None, limit: int = ROWS_MAX) -> dict[str, object]:
        """Query the selected snapshot. GRAPH ?g identifies the asserting bundle's base IRI."""
        with self._graph_lock, self._connection() as db:
            row = self._snapshot_row(db, snapshot)
            if row != self._graph_row:
                self._graph = self._load_graph(db, self._manifest(row))
                self._graph_row = row
            graph = self._graph
        return {"snapshot": row[0], **query_registry(graph, query, limit)}


def build_server(reader: SnapshotReader):
    """Expose retained snapshots directly over the same stdio transport as the live registry."""
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations
    from lokf.mcp_server import _version

    server = MCPServer("lokf-snapshots", version=_version(), instructions=(
        "Call get_snapshot to resolve the head and discover member base IRIs. Pass its snapshot "
        "to every read in a task. The graph, Markdown and vocabulary come from the same capture. "
        "Cited resources and remote URLs are references; their contents are outside this capture."
    ))

    def expose(fn):
        @wraps(fn)
        def call(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except SnapshotLookupError as exc:
                raise ToolError(str(exc)) from exc
        server.tool(annotations=ToolAnnotations(read_only_hint=True))(call)

    for fn in (reader.get_snapshot, reader.read_document, reader.get_vocabulary, reader.federated_sparql):
        expose(fn)
    return server
