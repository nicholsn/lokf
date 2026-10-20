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

    Source values containing whitespace need ./, ../ or an absolute path to
    be unambiguously local. Concept resource values are always identifiers or
    paths. Resolve symlinks before enforcing containment under the root.
    """
    root = root.resolve()
    for concept in bundle.concepts:
        values = [('resource', concept.data.get('resource'), False)]
        sources = concept.data.get('sources') or []
        if isinstance(sources, dict):
            sources = [sources]
        if isinstance(sources, list):
            values.extend((f'sources[{i}].resource', source.get('resource'), True)
                          for i, source in enumerate(sources) if isinstance(source, dict))
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
            try:
                path = (root / value).resolve()
                if not path.is_relative_to(root):
                    yield 'ERROR', f'{label} resolves outside resource root {root}: {value!r}'
                elif not (path.is_file() or path.is_dir()):
                    yield 'ERROR', f'{label} names no file or directory: {value!r} (looked at {path})'
            except (OSError, RuntimeError, ValueError) as exc:
                yield 'ERROR', f'{label} cannot resolve {value!r}: {exc}'
