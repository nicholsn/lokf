"""Opt-in local resource checks; remote identifiers are never dereferenced."""
from __future__ import annotations

import os
import re
from pathlib import Path, PureWindowsPath


def resource_root(bundle_dir: Path) -> Path:
    """Nearest enclosing Git root, otherwise the bundle's parent directory."""
    bundle_dir = bundle_dir.resolve()
    return next((p for p in (bundle_dir, *bundle_dir.parents) if (p / '.git').exists()),
                bundle_dir.parent)


def check_resources(bundle, root: Path):
    """Yield (severity, message), preserving scope descriptions as warnings.

    Source and exclusion values containing whitespace need ./, ../ or an
    absolute path to be unambiguously local. Concept resource values are always identifiers or
    paths. Resolve symlinks before enforcing containment under the root.
    """
    root = root.resolve()
    for concept in bundle.concepts:
        values = [('resource', concept.data.get('resource'), False)]
        # An exclusion names a material as a source does, scope descriptions included.
        for field in ('sources', 'exclusions'):
            values.extend((f'{field}[{i}].resource', entry.get('resource'), True)
                          for i, entry in _entries(concept, field))
        for key, value, source in values:
            if not isinstance(value, str) or not value:
                continue  # Shape and required fields are checked by the schema.
            label = f'{bundle.iri(concept)}: `{key}`'
            windows_path = bool(PureWindowsPath(value).drive)
            if not windows_path and re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', value):
                continue  # URI or CURIE, including explicitly scoped identifiers.
            explicit_path = value.startswith(('./', '../', '/', '.\\', '..\\')) or windows_path
            if source and any(c.isspace() for c in value) and not explicit_path:
                yield 'WARNING', (f'{label} is an unchecked scope description: {value!r}; '
                                  'prefix a local path with ./ to check it')
                continue
            if windows_path and os.name != 'nt':
                yield 'ERROR', f'{label} uses a Windows path that cannot be checked on this platform: {value!r}'
                continue
            if source and any(c in value for c in '*?['):
                # A pattern (docs/*.svg) names the files it matches; it holds
                # when it names existing resources, all inside the root.
                if value.startswith(('/', '\\')) or '..' in Path(value).parts:
                    yield 'ERROR', f'{label} is a pattern reaching outside resource root {root}: {value!r}'
                else:
                    try:
                        matched = False
                        for match in root.glob(value):
                            matched = True
                            path = match.resolve()
                            if not path.is_relative_to(root):
                                yield 'ERROR', f'{label} match resolves outside resource root {root}: {match}'
                            elif not (path.is_file() or path.is_dir()):
                                yield 'ERROR', f'{label} match names no file or directory: {match}'
                        if not matched:
                            yield 'ERROR', f'{label} matches no file or directory: {value!r} (under {root})'
                    except (OSError, RuntimeError, ValueError) as exc:
                        yield 'ERROR', f'{label} is not a pattern that can be checked: {value!r}: {exc}'
                continue
            try:
                path = (root / value).resolve()
                if not path.is_relative_to(root):
                    yield 'ERROR', f'{label} resolves outside resource root {root}: {value!r}'
                elif not (path.is_file() or path.is_dir()):
                    yield 'ERROR', f'{label} names no file or directory: {value!r} (looked at {path})'
            except (OSError, RuntimeError, ValueError) as exc:
                yield 'ERROR', f'{label} cannot resolve {value!r}: {exc}'


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
    """Yield a warning for each material one concept lists both as a source
    and as an exclusion: it cannot be derived from and left out at once."""
    for concept in bundle.concepts:
        used = {_same_material(e.get('resource')) for _, e in _entries(concept, 'sources')}
        for i, entry in _entries(concept, 'exclusions'):
            key = _same_material(entry.get('resource'))
            if key is not None and key in used:
                yield 'WARNING', (f'{bundle.iri(concept)}: `exclusions[{i}].resource` is also '
                                  f'one of its sources: {entry.get("resource")!r}')
