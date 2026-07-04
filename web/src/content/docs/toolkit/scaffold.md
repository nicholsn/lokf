---
title: Scaffold a knowledge base (lokf new)
description: Create a new, publishable LOKF knowledge-base repo — bundle, site, and agent skills — with one command.
---

`lokf new <name>` scaffolds a complete, publishable knowledge base — in the
spirit of linkml-cookiecutter. One command, and you (or an AI agent) can go from
an idea to a queryable knowledge graph *and* a website.

## Command

```bash
lokf new my-kb --title "My Knowledge Base" --base-iri https://myorg.github.io/my-kb/
```

Creates `my-kb/`:

```
my-kb/
  knowledge/                     # the LOKF bundle (index.md + example concepts)
  mkdocs.yml                     # renders the bundle as a website
  .github/workflows/pages.yml    # builds + publishes to GitHub Pages
  justfile                       # `just serve | rdf | tables | site` (via uvx)
  README.md
  .gitignore
  .claude/skills/                # the bundled agent skills
```

Everything runs through [`uvx`](https://docs.astral.sh/uv/), so the only
prerequisite is `uv` — no `pip install`.

## Then

```bash
cd my-kb
just serve     # explore the graph locally
```

Author concepts under `knowledge/` (see the two examples), listing each in
`knowledge/index.md`. Push to GitHub and set **Settings → Pages → Source** to
**GitHub Actions** to publish.

## Idea → published site, with an agent

The scaffold ships the bundled agent skills, so you can open the new repo in
[Claude Code](https://claude.com/claude-code) and say *"build a knowledge base
of …"*. The `scaffold-knowledge-base` and `author-concept` skills drive the
whole path — scaffold, author, validate, publish.
