"""Parse OKF/LOKF concept markdown into JSON-LD-ready dictionaries.

These helpers are the seed of the LOKF toolkit's parser: ``parse_concept``
splits a concept file into frontmatter + body, and ``isoify`` normalizes
YAML-parsed dates to the ISO-8601 ``Z`` form used by the committed RDF
projections.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

#: OKF type spellings normalized to their LOKF class names. OKF v0.2 writes
#: ``type: Attested Computation`` (§10); LOKF classes are single-word (the
#: GlossaryTerm precedent), and a spaced @type would not expand to a valid
#: vocab IRI. Applied in :func:`parse_concept`, so every consumer sees the
#: canonical form while authors may use either spelling.
OKF_TYPE_ALIASES = {
    "Attested Computation": "AttestedComputation",
    "Glossary Term": "GlossaryTerm",
}

#: The slots the schema types ``datetime``. OKF §5 makes every timestamp an
#: ISO 8601 datetime with an offset; LOKF bundles commonly write ``stale_after``
#: and the usage-window bounds as a bare ``YYYY-MM-DD``, which the JSON Schema
#: ``date-time`` format would reject. A bare date under one of these keys is
#: read as that day at 00:00:00Z, so both spellings validate and project as
#: ``xsd:dateTime``. ``tests/test_schema.py`` keeps this set equal to the
#: schema's datetime-ranged slots.
DATETIME_SLOTS = frozenset(
    {"at", "created", "timestamp", "stale_after", "from", "to", "last_modified"}
)

_BARE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def isoify(o, key: str | None = None):
    """Recursively convert ``datetime``/``date`` values to ISO-8601 strings.

    ``+00:00`` offsets are normalized to ``Z`` so JSON/RDF output matches the
    committed ``examples/*.nt`` projections byte-for-byte. *key* is the
    frontmatter key the value sits under: a bare date (YAML-typed or quoted)
    under a :data:`DATETIME_SLOTS` key becomes midnight UTC of that day.
    """
    if isinstance(o, dict):
        return {k: isoify(v, k) for k, v in o.items()}
    if isinstance(o, list):
        return [isoify(v, key) for v in o]
    if isinstance(o, dt.datetime):
        return o.isoformat().replace("+00:00", "Z")
    if isinstance(o, dt.date):
        o = o.isoformat()
    if key in DATETIME_SLOTS and isinstance(o, str) and _BARE_DATE.match(o):
        return f"{o}T00:00:00Z"
    return o


def parse_concept(path: str) -> dict:
    """Read one concept markdown file into a dict of frontmatter + ``body``.

    Raises ``ValueError`` with a clear message if the file has no ``---``
    delimited YAML frontmatter (e.g. a plain markdown or reserved file).
    """
    return parse_concept_text(read_markdown(Path(path)), path)


#: A delimiter of a frontmatter block: ``---`` at the start of a line, with
#: nothing after it but spaces or tabs. YAML also takes a comment or a value
#: after its ``---``; a delimiter does not.
_DELIMITER = re.compile(r"(?:\A|(?<=\A\ufeff)|(?<=[\r\n]))---[ \t]*(?=[\r\n]|\Z)")
#: The start of a page that means to open with a block: three dashes are its
#: first text, whatever follows them. Four or more are a rule.
_OPENS_WITH_DASHES = re.compile(r"[\ufeff \t\r\n]*---(?!-)")


def split_frontmatter(raw: str) -> tuple[str, str, str] | None:
    """Split markdown into ``(lead, frontmatter, body)``, or ``None`` with no closed block at the top.

    The block comes first: only a byte order mark or blank lines may stand before
    it, and they are returned as *lead* for a caller that rewrites the file. It
    opens and closes at the first two delimiter lines, so a ``---`` inside a
    value stays in the value.
    """
    opening = _DELIMITER.search(raw)
    if opening is None or raw[: opening.start()].strip("\ufeff \t\r\n"):
        return None
    closing = _DELIMITER.search(raw, opening.end())
    if closing is None:
        return None
    return raw[: opening.start()], raw[opening.end() : closing.start()], raw[closing.end() :]


class DocumentError(ValueError):
    """A Markdown input error with a filename and optional line number."""

    def __init__(self, where: str, reason: str, line: int | None = None):
        self.where = where
        self.reason = reason
        self.line = line
        super().__init__(f"{where}: {reason}")


class FrontmatterError(DocumentError):
    code = "document.frontmatter"


class DocumentEncodingError(DocumentError):
    code = "document.encoding"


def read_markdown(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentEncodingError(str(path), "Markdown must be encoded as UTF-8.") from exc


def _load_frontmatter(front: str, where: str, lead: str) -> dict:
    """The mapping a frontmatter block holds; *where* names the file in errors."""
    import yaml

    try:
        data = yaml.safe_load(front)
        if data is None:
            data = {}
    except (yaml.YAMLError, ValueError, OverflowError) as exc:
        # PyYAML's scalar constructors can reject a date or number without a YAML mark.
        mark = getattr(exc, "problem_mark", None)
        line = len(re.findall(r"\r\n?|\n", lead)) + mark.line + 1 if mark is not None else None
        raise FrontmatterError(where, f"frontmatter is not valid YAML: {exc}", line) from exc
    if not isinstance(data, dict):
        raise FrontmatterError(where, f"frontmatter must be a mapping, not {type(data).__name__}")
    return data


def parse_index_text(raw: str, where: str = "<text>") -> dict:
    """The frontmatter of a bundle's ``index.md``, or ``{}`` for a plain page.

    An index needs no block, unlike a concept. A page that opens with ``---``
    and has no closed block is an error all the same, as ``base_iri`` would go
    unread.
    """
    parts = split_frontmatter(raw)
    if parts:
        return isoify(_load_frontmatter(parts[1], where, parts[0]))
    if _OPENS_WITH_DASHES.match(raw):
        raise FrontmatterError(where, "frontmatter is not closed by '---' on a line of its own")
    return {}


def parse_concept_text(raw: str, where: str = "<text>") -> dict:
    """:func:`parse_concept` for markdown already read; *where* names it in errors."""
    data, _ = parse_concept_fields(raw, where)
    return data


def parse_concept_fields(raw: str, where: str) -> tuple[dict, tuple[str, ...]]:
    """Parse once, retaining which authored mappings were wrapped for projection."""
    parts = split_frontmatter(raw)
    if parts is None:
        raise FrontmatterError(
            where, "no YAML frontmatter (expected a block at the top of the file, "
            "opened and closed by '---' on a line of its own)"
        )
    lead, front, body = parts
    d = _load_frontmatter(front, where, lead)
    d["body"] = body.strip()
    if isinstance(d.get("type"), str) and d["type"] in OKF_TYPE_ALIASES:
        d["type"] = OKF_TYPE_ALIASES[d["type"]]
    # OKF v0.2 §5.2: a bare `verified: { by, at }` mapping MUST be read as a
    # one-element list. Normalized here so validation, RDF projection, and
    # trust derivation all see the canonical list form.
    mappings = tuple(key for key in ("verified", "refuted") if isinstance(d.get(key), dict))
    for key in mappings:
        d[key] = [d[key]]
    return isoify(d), mappings
