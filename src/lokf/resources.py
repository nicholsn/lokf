"""Opt-in local resource checks; remote identifiers are never dereferenced."""
from __future__ import annotations

import errno
import fnmatch
import os
import re
import stat
import sys
from pathlib import Path, PureWindowsPath


def resource_root(bundle_dir: Path) -> Path:
    """Nearest enclosing Git root, otherwise the bundle's parent directory."""
    bundle_dir = bundle_dir.resolve()
    return next((p for p in (bundle_dir, *bundle_dir.parents) if (p / '.git').exists()),
                bundle_dir.parent)


def kind_of(value: str, source: bool = True) -> str:
    """How a resource value is read, for the passes that check local resources.

    ``uri``: a URI or CURIE, never fetched. ``scope``: a prose scope
    description, which a source or exclusion may carry when the value has
    whitespace and no ./, ../ or absolute prefix; a concept's own resource is
    always a path or identifier. ``windows``: a drive path, checkable on
    Windows only. ``pattern``: a glob a source or exclusion may name.
    ``path``: anything else, resolved inside the resource root.
    """
    windows_path = bool(PureWindowsPath(value).drive)
    if not windows_path and re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', value):
        return 'uri'
    explicit_path = value.startswith(('./', '../', '/', '.\\', '..\\')) or windows_path
    if source and any(c.isspace() for c in value) and not explicit_path:
        return 'scope'
    if windows_path and os.name != 'nt':
        return 'windows'
    if source and any(c in value for c in '*?['):
        return 'pattern'
    return 'path'


def check_resources(bundle, root: Path):
    """Yield (severity, message) for check resources."""
    for _, _, _, severity, message in resource_findings(bundle, root):
        yield severity, message


def _glob_matches(root, pattern, errors):
    """Expand only matching branches, retaining scan errors that Path.glob suppresses."""
    parts = Path(pattern).parts
    if sys.version_info < (3, 13) and any('**' in part and part != '**' for part in parts):
        raise ValueError("'**' can only be an entire path component")
    directories_only = sys.version_info >= (3, 11) and pattern.endswith((os.sep, os.altsep or os.sep))
    pending = [(root, 0)]
    # Multiple recursive components can reach the same directory and suffix.
    seen = set() if parts.count('**') > 1 else None
    while pending:
        path, i = pending.pop()
        if seen is not None:
            if (path, i) in seen:
                continue
            seen.add((path, i))
        try:
            if i == len(parts):
                if directories_only:
                    if stat.S_ISDIR(path.stat().st_mode):
                        yield path
                elif sys.version_info < (3, 12) and not any(c in parts[-1] for c in '*?['):
                    # Older pathlib follows a symlink when matching a literal last component.
                    path.stat()
                    yield path
                else:
                    path.lstat()
                    yield path
                continue
            part = parts[i]
            if not any(c in part for c in '*?['):
                pending.append((path / part, i + 1))
                continue
            with os.scandir(path) as entries:
                if part == '**':
                    pending.append((path, i + 1))  # zero directories
                for entry in entries:
                    if part == '**':
                        if entry.is_dir(follow_symlinks=False):
                            pending.append((Path(entry.path), i))
                        elif i + 1 == len(parts) and sys.version_info >= (3, 13) and not directories_only:
                            pending.append((Path(entry.path), i + 1))
                    elif fnmatch.fnmatch(entry.name, part):
                        pending.append((Path(entry.path), i + 1))
        except (FileNotFoundError, NotADirectoryError):
            continue  # This branch cannot match.
        except OSError as exc:
            errors.append(exc)


def _inspect_resource(root, path):
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        return f"resolves outside resource root {root}: {path}"
    try:
        mode = resolved.stat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        mode = 0
    if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        return f"names no file or directory: {path}"
    return None


def resource_findings(bundle, root: Path, stats: dict | None = None):
    """Yield located findings, preserving scope descriptions as warnings.

    Source and exclusion values containing whitespace need ./, ../ or an
    absolute path to be unambiguously local. Concept resource values are always identifiers or
    paths. Resolve symlinks before enforcing containment under the root.
    """
    root = root.resolve()
    local = remote = unchecked = 0
    for concept in bundle.concepts:
        values = [('resource', '/resource', concept.data.get('resource'), False)]
        # An exclusion names a material as a source does, scope descriptions included.
        for field in ('sources', 'exclusions'):
            values.extend((f'{field}[{i}].resource', f'/{field}/{i}/resource', entry.get('resource'), True)
                          for i, entry in _entries(concept, field))
        where = concept.path.relative_to(bundle.root).as_posix()
        for key, pointer, value, source in values:
            if not isinstance(value, str) or not value:
                continue  # Shape and required fields are checked by the schema.
            label = f'{bundle.iri(concept)}: `{key}`'
            kind = kind_of(value, source)
            if kind == 'uri':
                remote += 1
                continue  # URI or CURIE, including explicitly scoped identifiers.
            if kind == 'scope':
                unchecked += 1
                yield 'resource.unchecked', where, pointer, 'WARNING', (f'{label} is an unchecked scope description: {value!r}; '
                                  'prefix a local path with ./ to check it')
                continue
            local += 1
            if kind == 'windows':
                yield 'resource.path', where, pointer, 'ERROR', f'{label} uses a Windows path that cannot be checked on this platform: {value!r}'
                continue
            pattern = kind == 'pattern'
            if pattern and (Path(value).anchor or value.startswith('\\') or '..' in Path(value).parts):
                yield 'resource.path', where, pointer, 'ERROR', f'{label} is a pattern reaching outside resource root {root}: {value!r}'
                continue
            errors = []
            try:
                paths = sorted(_glob_matches(root, value, errors)) if pattern else [root / value]
                if not paths and not errors:
                    yield 'resource.path', where, pointer, 'ERROR', f'{label} matches no file or directory: {value!r} (under {root})'
                for path in paths:
                    try:
                        problem = _inspect_resource(root, path)
                    except OSError as exc:
                        errors.append(exc)
                        continue
                    if problem:
                        yield 'resource.path', where, pointer, 'ERROR', f'{label} {problem}'
            except (RuntimeError, ValueError) as exc:
                yield 'resource.path', where, pointer, 'ERROR', f'{label} cannot resolve {value!r}: {exc}'
            incomplete = False
            for exc in sorted(errors, key=str):
                code = 'resource.path' if exc.errno in (errno.ELOOP, errno.ENAMETOOLONG) else 'resource.unavailable'
                if code == 'resource.unavailable':
                    incomplete = True
                yield code, where, pointer, 'ERROR', f'{label} cannot inspect {value!r}: {exc}'
            if incomplete:
                local -= 1
                unchecked += 1

    if stats is not None:
        stats.update(local=local, remote=remote, unchecked=unchecked)


def _entries(concept, field: str) -> list[tuple[int, dict]]:
    """The mapping entries of a list field with their positions in it."""
    entries = concept.data.get(field) or []
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        return []
    return [(i, e) for i, e in enumerate(entries) if isinstance(e, dict)]

def _same_material(value) -> str | None:
    """*value* as a comparison key: ``./docs/a.md``, ``docs/a.md`` and
    ``docs/a.md/`` name one material."""
    if not isinstance(value, str) or not value.strip():
        return None
    key = value.strip()
    while key.startswith('./'):
        key = key[2:]
    return key.rstrip('/') or key


def exclusion_conflicts(bundle):
    """Yield (severity, message) for exclusion conflicts."""
    for _, _, _, severity, message in exclusion_findings(bundle):
        yield severity, message


def exclusion_findings(bundle):
    """Yield a warning for each material one concept lists both as a source
    and as an exclusion: it cannot be derived from and left out at once."""
    for concept in bundle.concepts:
        used = {_same_material(e.get('resource')) for _, e in _entries(concept, 'sources')}
        for i, entry in _entries(concept, 'exclusions'):
            key = _same_material(entry.get('resource'))
            if key is not None and key in used:
                yield "resource.exclusion_conflict", concept.path.relative_to(bundle.root).as_posix(), f"/exclusions/{i}/resource", 'WARNING', (f'{bundle.iri(concept)}: `exclusions[{i}].resource` is also '
                                  f'one of its sources: {entry.get("resource")!r}')
