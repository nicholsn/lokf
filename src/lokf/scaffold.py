"""Scaffold a new LOKF knowledge-base repository.

`lokf new my-kb` writes a self-contained repo from the packaged template
(``lokf/templates/kb``): a starter **bundle** (``knowledge/``), a full **Astro
site** that renders the concepts and ships the interactive **graph browser**
(``/graph``) plus the ``graph.json`` / ``graph.jsonld`` projections, a GitHub
**Pages workflow**, a ``justfile`` that also drives the ``lokf`` toolkit via
``uvx``, and the bundled **agent skills** so an AI agent can author the
knowledge base from a prompt. In the spirit of linkml-cookiecutter: scaffold,
then start authoring (or point Claude at it).
"""
from __future__ import annotations

import pathlib
from importlib import resources
from urllib.parse import urlsplit

from lokf import agentskills

#: Path segments renamed on copy — dotfiles are stored dot-free so packaging
#: tools never skip them.
RENAMES = {"_github": ".github", "_gitignore": ".gitignore"}


def template_dir() -> pathlib.Path:
    """Return the packaged knowledge-base template (``lokf/templates/kb``)."""
    return pathlib.Path(str(resources.files("lokf") / "templates" / "kb"))


def _slug_title(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").strip().title()


def _tokens(name: str, title: str, base_iri: str) -> dict[str, str]:
    """The substitution map applied to every template file.

    ``site``/``base`` are split out of the base IRI so the Astro site works
    both at a domain root (base "/") and as a GitHub *project* page
    (base "/<repo>").
    """
    parts = urlsplit(base_iri)
    site = f"{parts.scheme}://{parts.netloc}"
    base = parts.path.rstrip("/") or "/"
    return {
        "__KB_NAME__": name,
        "__KB_TITLE__": title,
        "__KB_BASE_IRI__": base_iri,
        "__KB_SITE__": site,
        "__KB_BASE__": base,
    }


def new(name: str, path: str | pathlib.Path = ".",
        title: str | None = None, base_iri: str | None = None) -> pathlib.Path:
    """Create a new knowledge-base repo *name* under *path*; return its root.

    Refuses to overwrite an existing non-empty directory.
    """
    title = title or _slug_title(name)
    base_iri = base_iri or f"https://example.org/{name}/"
    if not base_iri.endswith("/"):
        base_iri += "/"

    root = pathlib.Path(path) / name
    if root.exists() and (root.is_file() or any(root.iterdir())):
        raise FileExistsError(f"{root} already exists and is not empty")

    tdir = template_dir()
    if not tdir.is_dir():
        raise RuntimeError(f"packaged knowledge-base template not found at {tdir}")
    tokens = _tokens(name, title, base_iri)
    for src in sorted(tdir.rglob("*")):
        if not src.is_file():
            continue
        rel = tuple(RENAMES.get(p, p) for p in src.relative_to(tdir).parts)
        dest = root.joinpath(*rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        for token, value in tokens.items():
            text = text.replace(token, value)
        dest.write_text(text, encoding="utf-8")

    # Drop the bundled agent skills in so an AI agent can author the KB.
    agentskills.install(root / ".claude" / "skills")
    return root
