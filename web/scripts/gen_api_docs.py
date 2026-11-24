#!/usr/bin/env python3
"""Generate the Starlight Python and CLI references from the lokf package.

Read module signatures, docstrings and the command tree during the web
prebuild with ``uv run python web/scripts/gen_api_docs.py``.
"""
from __future__ import annotations

import html
import importlib
import inspect
import pathlib
import re

from typer.main import get_command

import lokf
from lokf.cli import app

# Public toolkit modules, in reading order.
MODULES = [
    "lokf.model",
    "lokf.schema",
    "lokf.adapt",
    "lokf.parse",
    "lokf.rdf",
    "lokf.shacl",
    "lokf.validation",
    "lokf.trust",
    "lokf.resources",
    "lokf.excerpts",
    "lokf.events",
    "lokf.logs",
    "lokf.store",
    "lokf.server",
    "lokf.propose",
    "lokf.export",
    "lokf.views",
    "lokf.schema_docs",
    "lokf.tables",
    "lokf.scaffold",
    "lokf.registry",
    "lokf.registry_mcp",
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

REFERENCE = pathlib.Path(__file__).resolve().parent.parent / "src" / "content" / "docs" / "reference"


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


def _class_members(cls):
    """Report public methods, constructors and properties defined by this class."""
    for name, descriptor in vars(cls).items():
        if not _is_public(name):
            continue
        if isinstance(descriptor, property):
            yield name, descriptor, ""
        elif inspect.isfunction(descriptor) or isinstance(descriptor, (classmethod, staticmethod)):
            obj = getattr(cls, name)
            yield name, obj, _sig(obj)


def render() -> str:
    lines = [
        "---",
        "title: Python reference",
        "description: The lokf toolkit API — bundle model, vocabulary, RDF, store, server, and CLI helpers.",
        "sidebar:",
        "  order: 2",
        "---",
        "",
        "Generated from the toolkit modules. The following names can also be imported "
        "directly from `lokf`.",
        "",
        ", ".join(f"`{name}`" for name in lokf.__all__) + ".",
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
            for mname, mobj, signature in _class_members(cls):
                lines += [f"#### `{name}.{mname}{signature}`", ""]
                if _doc(mobj):
                    lines += [_doc(mobj), ""]
    return "\n".join(lines)


def _command_sections(command, ctx):
    yield f"## `{ctx.command_path}`"
    yield ""
    if command.help:
        yield command.help.split("\n\n", 1)[0].replace("\n", " ")
        yield ""
    yield f"```text\n{command.get_usage(ctx)}\n```"
    yield ""
    yield "| Argument or option | Meaning |"
    yield "| --- | --- |"
    for parameter in command.get_params(ctx):
        record = parameter.get_help_record(ctx)
        if record:
            label, description = record
            description = html.escape(" ".join(description.split()), quote=False).replace("|", r"\|")
            yield f"| `{label}` | {description} |"
    yield ""
    if hasattr(command, "list_commands"):
        for name in command.list_commands(ctx):
            child = command.get_command(ctx, name)
            if not child.hidden:
                with child.make_context(name, [], parent=ctx, resilient_parsing=True) as child_ctx:
                    yield from _command_sections(child, child_ctx)


def render_cli() -> str:
    command = get_command(app)
    lines = [
        "---",
        "title: CLI reference",
        "description: Commands, arguments, and options supported by the lokf CLI.",
        "sidebar:",
        "  order: 1",
        "---",
        "",
        "Each section gives the invocation and options for one command. "
        "Use `lokf COMMAND --help` to see the help for your installed version. "
        "For worked examples, see the [toolkit guide](/toolkit/).",
        "",
        "The package also installs `lokf-mcp` to run the [bundle MCP server](/toolkit/mcp/) "
        "and `lokf-build` to regenerate schema artifacts from a LOKF source checkout "
        "with the `build` extra.",
        "",
    ]
    with command.make_context("lokf", [], resilient_parsing=True) as ctx:
        lines.extend(_command_sections(command, ctx))
    return "\n".join(lines)


def main() -> None:
    REFERENCE.mkdir(parents=True, exist_ok=True)
    for filename, content in (("api.md", render()), ("cli.md", render_cli())):
        path = REFERENCE / filename
        path.write_text(content, encoding="utf-8")
        print(f"gen_api_docs: wrote {path.relative_to(REFERENCE.parents[3])}")


if __name__ == "__main__":
    main()
