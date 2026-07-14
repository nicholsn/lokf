#!/usr/bin/env python3
"""Generate the Starlight Python API reference from the lokf package.

Replaces mkdocstrings: imports each toolkit module and emits a Markdown page
of its public functions and classes (signatures + docstrings). Run in the
web prebuild (``uv run python web/scripts/gen_api_docs.py``); the output is
generated (gitignored) — edit the docstrings, not the page.
"""
from __future__ import annotations

import importlib
import inspect
import pathlib
import re

# Public toolkit modules, in reading order.
MODULES = [
    "lokf.model",
    "lokf.schema",
    "lokf.parse",
    "lokf.rdf",
    "lokf.store",
    "lokf.server",
    "lokf.propose",
    "lokf.export",
    "lokf.registry",
    "lokf.agentskills",
    "lokf.mcp_server",
    "lokf.build",
]

# RST cross-reference roles (written for mkdocstrings) → a plain code span.
_RST_ROLE = re.compile(r":(?:class|func|meth|attr|mod|obj|data|exc):`([^`]+)`")


def _clean(text: str) -> str:
    """Soften Sphinx/RST-isms so the docstrings read as plain Markdown."""
    text = _RST_ROLE.sub(r"`\1`", text)
    text = text.replace("::\n", ":\n")  # RST literal-block marker
    return text

OUT = pathlib.Path(__file__).resolve().parent.parent / "src" / "content" / "docs" / "reference" / "api.md"


def _sig(obj) -> str:
    try:
        return str(inspect.signature(obj))
    except (ValueError, TypeError):
        return "(…)"


def _doc(obj) -> str:
    return _clean(inspect.cleandoc(obj.__doc__)) if obj.__doc__ else ""


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _members(module):
    """Public functions and classes defined in *module* (not imported)."""
    funcs, classes = [], []
    for name, obj in vars(module).items():
        if not _is_public(name) or getattr(obj, "__module__", None) != module.__name__:
            continue
        if inspect.isfunction(obj):
            funcs.append((name, obj))
        elif inspect.isclass(obj):
            classes.append((name, obj))
    return funcs, classes


def _methods(cls):
    out = []
    for name, obj in vars(cls).items():
        if _is_public(name) and inspect.isfunction(obj):
            out.append((name, obj))
    return out


def render() -> str:
    lines = [
        "---",
        "title: Python reference",
        "description: The lokf toolkit API — bundle model, vocabulary, RDF, store, server, and CLI helpers.",
        "sidebar:",
        "  order: 2",
        "---",
        "",
        "Generated from the installed `lokf` package. Every entry below is the "
        "real signature and docstring of the shipped code.",
        "",
    ]
    for mod_name in MODULES:
        module = importlib.import_module(mod_name)
        lines += [f"## `{mod_name}`", ""]
        mdoc = _doc(module)
        if mdoc:
            lines += [mdoc, ""]
        funcs, classes = _members(module)
        for name, obj in funcs:
            lines += [f"### `{name}{_sig(obj)}`", ""]
            if _doc(obj):
                lines += [_doc(obj), ""]
        for name, cls in classes:
            lines += [f"### `class {name}`", ""]
            if _doc(cls):
                lines += [_doc(cls), ""]
            for mname, mobj in _methods(cls):
                lines += [f"#### `{name}.{mname}{_sig(mobj)}`", ""]
                if _doc(mobj):
                    lines += [_doc(mobj), ""]
    return "\n".join(lines)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"gen_api_docs: wrote {OUT.relative_to(OUT.parents[4])}")


if __name__ == "__main__":
    main()
