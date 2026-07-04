"""Scaffold a new LOKF knowledge-base repository.

`lokf new my-kb` writes a self-contained repo: a starter **bundle**, a **MkDocs
site** that publishes it to **GitHub Pages**, a `justfile` that drives the `lokf`
toolkit via `uvx` (no install needed), and the bundled **agent skills** so an AI
agent can author the knowledge base from a prompt. In the spirit of
linkml-cookiecutter: scaffold, then start authoring (or point Claude at it).
"""
from __future__ import annotations

import pathlib

from lokf import agentskills

CONTEXT_URL = "https://raw.githubusercontent.com/nicholsn/lokf/main/lokf.context.jsonld"


def _slug_title(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").strip().title()


def _files(name: str, title: str, base_iri: str) -> dict[str, str]:
    """The scaffold as ``{relative_path: content}``."""
    return {
        # --- the bundle ----------------------------------------------------
        "knowledge/index.md": f"""---
lokf_version: "0.1"
okf_version: "0.1"
base_iri: {base_iri}
context: {CONTEXT_URL}
title: {title}
description: A LOKF knowledge base — markdown concepts that are also a graph.
license: https://creativecommons.org/licenses/by/4.0/
---

# {title}

A [LOKF](https://lokf.nolan-nichols.com) knowledge base. Every markdown file
under `knowledge/` is one concept; together they are a queryable knowledge graph
*and* this website. Replace the examples below with your own.

## Glossary

* [Active User](glossary/active-user.md) — an example defined term.

## Metrics

* [Weekly Active Users](metrics/weekly-active-users.md) — an example metric.
""",
        "knowledge/glossary/active-user.md": """---
type: GlossaryTerm
title: Active User
definition: A user who has performed a qualifying action in the period of interest.
tags: [example]
---

# Active User

An example concept. Delete it and add your own — each file is one concept with
YAML frontmatter (a `type` plus fields) and a markdown body.
""",
        "knowledge/metrics/weekly-active-users.md": f"""---
type: Metric
title: Weekly Active Users
unit: users
formula: COUNT(DISTINCT user_id) over a trailing 7-day window
measures: [{base_iri}glossary/active-user]
tags: [example]
---

# Weekly Active Users

An example metric that **measures** the [Active User](../glossary/active-user.md)
term. `measures` is a typed relation — it becomes an edge in the graph.
""",
        # --- the site ------------------------------------------------------
        "mkdocs.yml": f"""site_name: {title}
theme:
  name: material
# The bundle IS the docs: index.md is the home page, each concept a page.
docs_dir: knowledge
""",
        ".github/workflows/pages.yml": """name: pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: pip install mkdocs-material
      - run: mkdocs build --strict
      - uses: actions/upload-pages-artifact@v5
        with:
          path: site
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v5
""",
        # --- project glue (uvx: no install needed) -------------------------
        "justfile": """# List recipes
default:
    @just --list

# Interactive graph explorer (local SPARQL endpoint + viz)
serve:
    uvx --from lokf lokf serve knowledge

# Project the bundle to RDF (Turtle) on stdout
rdf:
    uvx --from lokf lokf convert knowledge --format ttl

# Project the bundle to linked tables (CSV under build/tables)
tables:
    uvx --from 'lokf[tables]' lokf tables knowledge --format csv --output build/tables

# Build the static site locally (output: site/)
site:
    uvx --with mkdocs-material mkdocs build
""",
        "README.md": f"""# {title}

A [LOKF](https://lokf.nolan-nichols.com) knowledge base. Every markdown file in
`knowledge/` is one concept; together they are a queryable knowledge graph *and*
a website.

## Author

Add concept files under `knowledge/` (see the two examples). Each has YAML
frontmatter (a `type` and fields) plus a markdown body; list new concepts in
`knowledge/index.md`. Relations between concepts (`measures`, `dependsOn`,
`isPartOf`, …) are typed links that become edges in the graph.

Prefer an AI agent? The bundled skills in `.claude/skills/` drive the whole
workflow — open this repo in [Claude Code](https://claude.com/claude-code) and
ask it to build out the knowledge base from your idea.

## Work with it

```bash
just serve    # interactive graph explorer
just rdf      # project to RDF / Turtle
just tables   # project to linked tables (CSV)
just site     # build the static site
```

These use [`uvx`](https://docs.astral.sh/uv/), so you only need `uv` installed —
no `pip install`.

## Publish to GitHub Pages

1. Set `base_iri` in `knowledge/index.md` to your published URL.
2. Push to GitHub; in **Settings → Pages**, set the source to **GitHub Actions**.
3. The `pages` workflow builds the site and publishes it on every push to `main`.

## Responsible AI use

This knowledge base may be authored with AI assistance. You own everything you
commit — understand it, verify it, and don't credit an AI as a co-author. See
the [LOKF AI Covenant](https://github.com/nicholsn/lokf/blob/main/AI_COVENANT.md).
""",
        ".gitignore": """# build output
site/
build/
lokf-tables/

# python / os
__pycache__/
*.pyc
.venv/
.DS_Store
""",
    }


def new(name: str, path: str | pathlib.Path = ".",
        title: str | None = None, base_iri: str | None = None) -> pathlib.Path:
    """Create a new knowledge-base repo *name* under *path*; return its root.

    Refuses to overwrite an existing non-empty directory.
    """
    title = title or _slug_title(name)
    base_iri = (base_iri or f"https://example.org/{name}/")
    if not base_iri.endswith("/"):
        base_iri += "/"

    root = pathlib.Path(path) / name
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"{root} already exists and is not empty")

    for rel, content in _files(name, title, base_iri).items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    # Drop the bundled agent skills in so an AI agent can author the KB.
    agentskills.install(root / ".claude" / "skills")
    return root
