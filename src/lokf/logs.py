"""Validate reserved change logs independently of concept frontmatter."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path


def check_logs(root: Path):
    """Yield (severity, file, line, message); missing logs are valid.

    Markdown parsing keeps headings in fenced code, HTML, and indented code
    out of the date checks. All level-two headings represent date groups.
    """
    from markdown_it import MarkdownIt

    parser = MarkdownIt()
    for path in sorted(root.rglob("log.md")):
        tokens = parser.parse(path.read_text(encoding="utf-8"))
        seen = set()
        previous = None
        for i, token in enumerate(tokens):
            if token.type != "heading_open" or token.tag != "h2":
                continue
            heading = tokens[i + 1].content
            line = token.map[0] + 1
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", heading):
                    raise ValueError
                date = dt.date.fromisoformat(heading)
            except ValueError:
                yield "ERROR", path, line, f"date heading must be a valid YYYY-MM-DD date: {heading!r}"
                continue
            if date in seen:
                yield "WARNING", path, line, f"duplicate date heading: {heading}"
            if previous is not None and date > previous:
                yield "WARNING", path, line, f"date headings must be newest first: {heading}"
            seen.add(date)
            previous = date
