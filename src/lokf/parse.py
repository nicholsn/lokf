"""Parse OKF/LOKF concept markdown into JSON-LD-ready dictionaries.

These helpers are the seed of the LOKF toolkit's parser: ``parse_concept``
splits a concept file into frontmatter + body, and ``isoify`` normalizes
YAML-parsed dates to the ISO-8601 ``Z`` form used by the committed RDF
projections.
"""
from __future__ import annotations

import datetime as dt
import re

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
    return parse_concept_text(open(path, encoding="utf-8").read(), path)


#: A delimiter of a frontmatter block: ``---`` at the start of a line, with
#: nothing after it but spaces or tabs. YAML also takes a comment or a value
#: after its ``---``; a delimiter does not.
_DELIMITER = re.compile(r"(?:\A|(?<=\A\ufeff)|(?<=[\r\n]))---[ \t]*(?=[\r\n]|\Z)")
#: The start of a page that means to open with a block: three dashes are its
#: first text, whatever follows them. Four or more are a rule.
_OPENS_WITH_DASHES = re.compile(r"[\ufeff\s]*---(?!-)")


def split_frontmatter(raw: str) -> tuple[str, str, str] | None:
    """Split markdown into ``(preamble, frontmatter, body)``, or ``None`` with no closed block.

    The block opens and closes at the first two delimiter lines, so a ``---``
    inside a value stays in the value. A preamble before the block, a byte
    order mark included, is returned whole for a caller that rewrites the file.
    """
    opening = _DELIMITER.search(raw)
    closing = _DELIMITER.search(raw, opening.end()) if opening else None
    if closing is None:
        return None
    return raw[: opening.start()], raw[opening.end() : closing.start()], raw[closing.end() :]


def _load_frontmatter(front: str, where: str) -> dict:
    """The mapping a frontmatter block holds; *where* names the file in errors."""
    import yaml

    try:
        data = yaml.safe_load(front) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{where}: frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{where}: frontmatter must be a mapping, not {type(data).__name__}")
    return data


def parse_index_text(raw: str, where: str = "<text>") -> dict:
    """The frontmatter of a bundle's ``index.md``, or ``{}`` for a plain page.

    An index needs no block, so a pair of ``---`` rules lower down a plain page
    is not one: only a block at the very top counts. A page that opens with
    ``---`` and has no such block is an error, as ``base_iri`` would go unread.
    """
    parts = split_frontmatter(raw)
    if parts and not parts[0].strip("\ufeff \t\r\n"):
        return isoify(_load_frontmatter(parts[1], where))
    if _OPENS_WITH_DASHES.match(raw):
        raise ValueError(f"{where}: frontmatter is not closed by '---' on a line of its own")
    return {}


def parse_concept_text(raw: str, where: str = "<text>") -> dict:
    """:func:`parse_concept` for markdown already read; *where* names it in errors."""
    parts = split_frontmatter(raw)
    if parts is None:
        raise ValueError(
            f"{where}: no YAML frontmatter (expected a block opened and closed by "
            "'---' on a line of its own)"
        )
    _, front, body = parts
    d = _load_frontmatter(front, where)
    d["body"] = body.strip()
    if d.get("type") in OKF_TYPE_ALIASES:
        d["type"] = OKF_TYPE_ALIASES[d["type"]]
    # OKF v0.2 §5.2: a bare `verified: { by, at }` mapping MUST be read as a
    # one-element list. Normalized here so validation, RDF projection, and
    # trust derivation all see the canonical list form.
    if isinstance(d.get("verified"), dict):
        d["verified"] = [d["verified"]]
    # LOKF's `refuted` is `verified`'s negative counterpart and reads the same way.
    if isinstance(d.get("refuted"), dict):
        d["refuted"] = [d["refuted"]]
    return isoify(d)
