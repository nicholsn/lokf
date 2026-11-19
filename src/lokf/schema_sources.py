"""Capture local LinkML inputs before interpreting or identifying them.

LinkML resolves imports; this module supplies captured bytes to its loaders.
Warm reads compare bytes, not timestamps. Remote imports retain their existing
uncached reading path, but cannot claim a complete local content identity.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from functools import cached_property, lru_cache, wraps
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
from threading import RLock
from types import MethodType

import yaml

CACHE_SIZE = 32
MAX_SOURCES = 256


class UnpinnedImport(ValueError):
    """An import cannot be captured as local source bytes."""


def cache_per_root(build):
    """Retain the latest interpretation of each of the most recent roots."""
    @lru_cache(maxsize=CACHE_SIZE)
    def root_cache(path):
        return lru_cache(maxsize=1)(build)

    @wraps(build)
    def cached(inputs, *args):
        return root_cache(inputs.sources[0].path)(inputs, *args)

    cached.cache_clear = root_cache.cache_clear
    cached.cache_info = root_cache.cache_info  # occupancy counts roots
    return cached


@lru_cache(maxsize=CACHE_SIZE)
def parsed(data: bytes) -> dict:
    value = yaml.safe_load(data)
    if not isinstance(value, dict):
        raise ValueError("A schema must be a YAML mapping")
    return value


def _definition(data: bytes, path: str):
    from copy import deepcopy
    from linkml_runtime.linkml_model.meta import SchemaDefinition
    from linkml_runtime.loaders import yaml_loader

    result = yaml_loader.load(deepcopy(parsed(data)), target_class=SchemaDefinition)
    result.source_file = path
    return result


def local_view_caches(view):
    """SchemaView's class-level memoizers otherwise retain every view forever.
    Give a captured view its own bounded memoizers and lifetime instead.
    """
    from linkml_runtime.utils.schemaview import SchemaView

    for name, method in vars(SchemaView).items():
        if hasattr(method, "cache_info") and hasattr(method, "__wrapped__"):
            setattr(view, name, lru_cache(maxsize=128)(MethodType(method.__wrapped__, view)))
    return view


def _import_path(view, imp: str, source) -> Path:
    from linkml_runtime.utils.context_utils import map_import

    name = map_import(view._resolved_importmap(), view.namespaces, imp)
    if "://" in name:
        raise UnpinnedImport(f"Import {imp!r} is not a local file: {name}")
    path = Path(name + ".yaml")
    return path if path.is_absolute() else Path(source.source_file).parent / path


@dataclass(frozen=True)
class Source:
    path: str
    data: bytes


@dataclass(frozen=True)
class SchemaInputs:
    sources: tuple[Source, ...]  # root first
    keys: tuple[tuple[str, int], ...]  # SchemaView closure keys -> sources
    edges: tuple[tuple[int, ...], ...]  # authoring import order per source
    locators: tuple[tuple[str, str], ...]  # detect retargeted symlinks too

    def unchanged(self) -> bool:
        return (all(str(Path(p).resolve()) == target for p, target in self.locators)
                and all(Path(s.path).read_bytes() == s.data for s in self.sources))

    def view(self):
        from linkml_runtime.utils.schemaview import SchemaView

        definitions = [_definition(s.data, s.path) for s in self.sources]
        view = local_view_caches(SchemaView(definitions[0]))
        view.schema_map = {key: definitions[index] for key, index in self.keys}
        view.imports_closure()  # all inputs are already present; no file reads
        return view

    def context_inputs(self) -> tuple[dict, dict]:
        """Give SchemaLoader unique in-memory import keys, including for two
        directories both importing a file called `types`. Never re-open a source.
        Only loader routing changes; schema IDs, prefixes and terms are untouched.
        """
        from copy import deepcopy

        names = [f"https://lokf.invalid/captured-input/{i}" for i in range(len(self.sources))]
        documents = [deepcopy(parsed(s.data)) for s in self.sources]
        for i, doc in enumerate(documents):
            doc["imports"] = [names[j] for j in self.edges[i]]
        return documents[0], dict(zip(names, documents))

    def metadata(self) -> dict:
        # Callers may edit their result. Keep only the immutable encoding here.
        return json.loads(self._encoded_metadata)

    @cached_property
    def _encoded_metadata(self) -> str:
        hashes = [sha256(s.data).hexdigest() for s in self.sources]
        records = [{"id": parsed(s.data).get("id"), "sha256": hashes[i],
                    "imports": [hashes[j] for j in self.edges[i]]}
                   for i, s in enumerate(self.sources)]
        identity = {"format": "lokf-schema-inputs-v1", "root_sha256": hashes[0],
                    "sources": sorted(records, key=lambda r: (str(r["id"]), r["sha256"])),
                    "linkml_runtime": version("linkml-runtime")}
        digest = sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return json.dumps({"complete": True, "revision": f"sha256:{digest}", **identity}, separators=(",", ":"))


_cache: OrderedDict[str, SchemaInputs] = OrderedDict()
_lock = RLock()


def capture(path: str | Path) -> SchemaInputs:
    """Capture a bounded closure using LinkML's own resolution rules.

    Cached interpretations are reusable only while every source still has the
    same bytes. Parsing and generation consume these bytes, so a later edit can
    never attach a new hash to an old interpretation. This is not a filesystem
    transaction or a historical knowledge-snapshot service.
    """
    resolved = str(Path(path).resolve())
    with _lock:
        previous = _cache.get(resolved)
    if previous is not None and previous.unchanged():
        with _lock:
            if resolved in _cache:
                _cache.move_to_end(resolved)
        return previous

    from linkml_runtime.utils.schemaview import SchemaView

    sources: list[Source] = []
    positions: dict[str, int] = {}
    locators: dict[str, str] = {}

    def read(location: Path):
        canonical = str(location.resolve())
        locators[str(location)] = canonical
        if canonical not in positions:
            if len(sources) >= MAX_SOURCES:
                raise ValueError(f"Schema import closure exceeds {MAX_SOURCES} files")
            positions[canonical] = len(sources)
            sources.append(Source(canonical, location.read_bytes()))
        return _definition(sources[positions[canonical]].data, canonical)

    class CapturedView(SchemaView):
        def load_import(self, imp, from_schema=None):
            return read(_import_path(self, imp, from_schema or self.schema))

    view = local_view_caches(CapturedView(read(Path(resolved))))
    view.imports_closure()
    keys = tuple((str(key), positions[str(schema.source_file)])
                 for key, schema in view.schema_map.items())
    definitions = {str(schema.source_file): schema for schema in view.schema_map.values()}
    edges = []
    for source in sources:
        definition = definitions[source.path]
        targets = []
        for imp in definition.imports:
            location = _import_path(view, imp, definition)
            canonical = str(location.resolve())
            if canonical not in positions:
                raise ValueError(f"Ambiguous schema import {imp!r} in {source.path}")
            locators[str(location)] = canonical
            targets.append(positions[canonical])
        edges.append(tuple(targets))
    inputs = SchemaInputs(tuple(sources), keys, tuple(edges), tuple(sorted(locators.items())))
    # Detect edits/removals while traversing; never cache a partly changed closure.
    if not inputs.unchanged():
        raise ValueError("Schema inputs changed while being read; retry the operation")
    with _lock:
        _cache[resolved] = inputs
        _cache.move_to_end(resolved)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return inputs
