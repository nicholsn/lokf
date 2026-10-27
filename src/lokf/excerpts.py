"""Opt-in check that each ``sources[].excerpt`` occurs in its local resource.

An excerpt is a verbatim copy of the passage in ``resource`` that the concept
relies on (SPEC §5.4). This pass finds it there under one grammar (SPEC §9,
"Excerpt checks"), so a quote that drifted from its source is caught by the
toolkit rather than by a reader. The cases of the grammar are a corpus,
``tests/fixtures/excerpt-corpus.yaml``, that any other checker can run.

- Whitespace runs collapse to one space and case is folded; punctuation is
  kept, since a dropped "not" matters where a dropped comma rarely does.
- ``...`` (also ``…``, ``[...]`` and ``[…]``) marks a gap: an excerpt is at
  most two spans, found in source order inside one heading section. A line
  beginning ``#`` or ``##`` outside a fenced code block starts a section of a
  Markdown resource; any other file is one section.
- ``[sic]``, a bracketed editorial note of at most forty characters, is
  skipped; a longer one is matched as written, as is a Markdown resource's
  own syntax: ``**no**`` is the passage, not ``no``.

A URL is never fetched, as ``--check-resources`` never fetches one. A scope
description, a directory or a pattern holds no text, so an excerpt on one is
an error, as is a file that is not text.
"""
from __future__ import annotations

import re
from pathlib import Path

from lokf.resources import _entries, kind_of

GAP = re.compile(r"\[\s*(?:\.{3}|…)\s*\]|\.{3}|…")
NOTE = re.compile(r"\[[^\[\]\n]{1,40}\]")
HEADING = re.compile(r"^#{1,2}\s")
_SPACE = re.compile(r"\s+")
MARKDOWN = frozenset({".md", ".mdx", ".markdown", ".mkd"})
#: A resource over this size is reported unchecked rather than read.
MAX_BYTES = 16 * 1024 * 1024


def normalize(text: str) -> str:
    """Whitespace runs to one space, case folded, punctuation kept."""
    return _SPACE.sub(" ", text).strip().casefold()


def spans(excerpt: str) -> list[str]:
    """The excerpt's spans around its gaps, notes removed and normalized;
    an empty span (a leading or trailing gap) is dropped."""
    return [s for part in GAP.split(excerpt) if (s := normalize(NOTE.sub(" ", part)))]


def sections(text: str, markdown: bool) -> list[str]:
    """The heading sections of a Markdown text, else the whole text."""
    if not markdown:
        return [text]
    out: list[str] = []
    current: list[str] = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence is not None:
            if (marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence)
                    and not marker[2].strip()):
                fence = None
        elif marker and (marker[1][0] != "`" or "`" not in marker[2]):
            fence = marker[1]
        elif HEADING.match(line) and current:
            out.append("".join(current))
            current = []
        current.append(line)
    out.append("".join(current))
    return out


def find(excerpt: str, text: str, markdown: bool = True, where: str = "the resource") -> str | None:
    """None when *excerpt* occurs in *text* under the grammar, else why not."""
    parts = spans(excerpt)
    if not parts:
        return "is empty"
    if len(parts) > 2:
        return f"joins {len(parts)} spans; at most two, around one `...`"
    whole = normalize(text)
    first = parts[0]
    if len(parts) == 1:
        return None if first in whole else f"is not in {where}"
    second = parts[1]
    if first not in whole:
        return f"starts with a span that is not in {where}"
    if second not in whole:
        return f"ends with a span that is not in {where}"
    for section in sections(text, markdown):
        n = normalize(section)
        i = n.find(first)
        while i != -1:
            if n.find(second, i + len(first)) != -1:
                return None
            i = n.find(first, i + 1)
    return f"has two spans that are not in order inside one heading section of {where}"


def check_excerpts(bundle, root: Path, stats: dict | None = None):
    """Yield (severity, message) for each ``sources[].excerpt`` not found in
    its local resource. *stats*, when given, receives ``local``, the excerpts
    checked against a file, and ``remote``, the ones on a URL, which is never
    fetched, plus ``unchecked`` for local excerpts skipped by the size limit."""
    root = root.resolve()
    local = remote = unchecked = 0
    for concept in bundle.concepts:
        for i, entry in _entries(concept, "sources"):
            excerpt, value = entry.get("excerpt"), entry.get("resource")
            if not isinstance(excerpt, str) or not isinstance(value, str) or not value:
                continue  # Absent, or a shape the schema reports.
            label = f"{bundle.iri(concept)}: `sources[{i}].excerpt` ({_short(excerpt)})"
            kind = kind_of(value)
            if kind == "uri":
                remote += 1
                continue
            if kind == "scope":
                yield "ERROR", f"{label} quotes a scope description, which holds no text: {value!r}"
                continue
            if kind == "windows":
                yield "ERROR", f"{label} names a Windows path that cannot be checked on this platform: {value!r}"
                continue
            if kind == "pattern":
                yield "ERROR", f"{label} quotes a pattern; an excerpt needs one file: {value!r}"
                continue
            try:
                path = (root / value).resolve()
            except (OSError, RuntimeError, ValueError) as exc:
                yield "ERROR", f"{label} cannot resolve {value!r}: {exc}"
                continue
            if not path.is_relative_to(root):
                yield "ERROR", f"{label} resolves outside resource root {root}: {value!r}"
            elif path.is_dir():
                yield "ERROR", f"{label} quotes a directory; an excerpt needs a file: {value!r}"
            elif not path.is_file():
                yield "ERROR", f"{label} names no file: {value!r} (looked at {path})"
            else:
                local += 1
                finding = _check_file(excerpt, path, value)
                if finding and finding[0] == "WARNING":
                    unchecked += 1
                    local -= 1
                if finding:
                    yield finding[0], f"{label} {finding[1]}"
    if stats is not None:
        stats["local"], stats["remote"], stats["unchecked"] = local, remote, unchecked


def _check_file(excerpt: str, path: Path, value: str) -> tuple[str, str] | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return "WARNING", f"is not checked against a file over {MAX_BYTES >> 20} MiB: {value!r}"
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return "WARNING", f"is not checked against a file over {MAX_BYTES >> 20} MiB: {value!r}"
    except OSError as exc:
        return "ERROR", f"cannot read {value!r}: {exc}"
    if b"\x00" in data[:8192]:
        return "ERROR", f"quotes a file that is not text: {value!r}"
    problem = find(excerpt, data.decode("utf-8", errors="replace"),
                   markdown=path.suffix.lower() in MARKDOWN, where=repr(value))
    return ("ERROR", problem) if problem else None


def _short(excerpt: str) -> str:
    flat = _SPACE.sub(" ", excerpt).strip()
    return repr(flat[:40] + ("…" if len(flat) > 40 else ""))
