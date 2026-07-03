"""Access and install the Claude Code agent skills bundled with LOKF.

The skills live under ``lokf/skills/<name>/SKILL.md``, each a directory with a
``SKILL.md`` carrying YAML frontmatter (``name``/``description``) and a markdown
body of instructions that drive the real ``lokf`` CLI. This module locates them
(zip-safe, like :mod:`lokf.schema`), lists their frontmatter, and copies the
tree into a project's ``.claude/skills`` so an agent can use them.
"""
from __future__ import annotations

import pathlib
import shutil
from importlib import resources

import yaml


def skills_dir() -> pathlib.Path:
    """Return the packaged skills directory (``lokf/skills``)."""
    return pathlib.Path(str(resources.files("lokf") / "skills"))


def _frontmatter(skill_md: pathlib.Path) -> dict:
    """Parse the YAML frontmatter block delimited by ``---`` from a SKILL.md."""
    text = skill_md.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def list_skills() -> list[tuple[str, str]]:
    """Return ``(name, description)`` from each skill's SKILL.md frontmatter."""
    skills = []
    for skill in sorted(skills_dir().iterdir()):
        md = skill / "SKILL.md"
        if not md.is_file():
            continue
        meta = _frontmatter(md)
        skills.append((meta.get("name", skill.name), meta.get("description", "")))
    return skills


def install(dest: str | pathlib.Path | None = None) -> pathlib.Path:
    """Copy the skills tree into *dest* (default ``.claude/skills``); return it.

    Parents are created and same-named skills are overwritten in place.
    """
    dest = pathlib.Path(dest) if dest is not None else pathlib.Path(".claude/skills")
    dest.mkdir(parents=True, exist_ok=True)
    for skill in skills_dir().iterdir():
        if not (skill / "SKILL.md").is_file():
            continue
        target = dest / skill.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill, target)
    return dest
