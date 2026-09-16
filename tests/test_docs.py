"""Guards against documentation drifting from the code.

The prose in README/SPEC quotes the package version in a few places, and those
sat at 0.5.0 while the package shipped 0.7.0 — two releases of silent drift,
because nothing checked. These assert the documented surface still matches the
real one.
"""
import pathlib
import re
from importlib.metadata import version

import pytest

from lokf.cli import app

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = [ROOT / "README.md", ROOT / "SPEC.md"]

#: Prose patterns that quote the *package* version. Each must capture it in
#: group 1. Add a pattern here when a doc starts quoting the version somewhere
#: new, so it is covered by the drift check rather than silently going stale.
VERSION_CLAIMS = [
    r"carry their own version \(currently (\d+\.\d+\.\d+)\)",
    r"the `lokf` package at (\d+\.\d+\.\d+)",
    r"version \(currently (\d+\.\d+\.\d+)\), so the toolkit",
    r"realized by schema (\d+\.\d+\.\d+)",
]


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_docs_quote_the_current_package_version(doc):
    current = version("lokf")
    text = doc.read_text(encoding="utf-8")
    found = 0
    for pattern in VERSION_CLAIMS:
        for m in re.finditer(pattern, text):
            found += 1
            assert m.group(1) == current, (
                f"{doc.name} says {m.group(1)!r} where the package is {current!r} "
                f"(pattern: {pattern}). Update the prose when bumping the version."
            )
    if doc.name == "SPEC.md":
        assert found, "SPEC.md no longer states the package version anywhere"


def test_every_documented_lokf_command_exists():
    """Every `lokf <cmd>` in a fenced shell block must be a real command."""
    real = {c.name or c.callback.__name__ for c in app.registered_commands}
    files = [
        p
        for p in ROOT.rglob("*.md*")
        if not any(x in p.parts for x in (".venv", "node_modules", ".git", "dist", "site"))
    ]
    unknown = set()
    for f in files:
        blocks = re.findall(
            r"```(?:bash|sh|console)\n(.*?)```", f.read_text(encoding="utf-8", errors="ignore"), re.S
        )
        for line in (l.strip().lstrip("$ ").strip() for b in blocks for l in b.splitlines()):
            m = re.match(r"^(?:uv run |uvx --from \S+ )?lokf\s+([a-z][\w-]*)", line)
            if m and m.group(1) not in real:
                unknown.add((f.relative_to(ROOT).as_posix(), m.group(1)))
    assert not unknown, f"documented commands that do not exist: {sorted(unknown)}"


def test_no_broken_relative_links_in_the_root_docs():
    broken = []
    for doc in DOCS + [ROOT / "CONTRIBUTING.md", ROOT / "AI_COVENANT.md", ROOT / "SECURITY.md"]:
        for _, target in re.findall(
            r"\[([^\]]*)\]\(([^)]+)\)", _strip_code(doc.read_text(encoding="utf-8"))
        ):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if not (doc.parent / target.split("#")[0]).exists():
                broken.append(f"{doc.name} -> {target}")
    assert not broken, f"broken relative links: {broken}"
