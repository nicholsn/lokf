"""Consumer-side trust, provenance, and lifecycle semantics (OKF v0.2 §5).

OKF v0.2 records trust *signals* in frontmatter; deriving meaning from them
is the consumer's job. This module implements the derivations the spec
defines, on plain concept-frontmatter dicts (:attr:`Concept.data`):

- :func:`verifications` — the ``verified`` events, normalizing the bare
  single-mapping form to a one-element list (a consumer MUST, §5.2).
- :func:`trust_tier` — unverified / machine-confirmed / human-reviewed,
  keyed off the ``human:`` actor prefix (§5.3, §7).
- :func:`effective_status` — ``status`` with the specified default
  (absent ⇒ ``stable``, §5.4).
- :func:`is_stale` — plain date comparison against ``stale_after`` (§5.5).
- :func:`generated_at` — ``generated.at`` with the sanctioned fallback to
  the superseded v0.1 ``timestamp`` field (§13.1).
- :func:`revised_at` / :func:`last_changed_at` — the latest in-place edit a
  producer records apart from ``generated`` (LOKF ``revised``), and the
  last meaningful change read as the later of the two.

All functions are total: malformed or missing families degrade to the
"absent" reading, never an exception — OKF consumers MUST NOT reject a
concept over optional frontmatter (§11).
"""
from __future__ import annotations

import datetime as dt

#: Trust tiers, lowest to highest (§5.3).
UNVERIFIED = "unverified"
MACHINE_CONFIRMED = "machine-confirmed"
HUMAN_REVIEWED = "human-reviewed"

#: Lifecycle states (§5.4). Absent ``status`` means stable.
STATUSES = ("draft", "stable", "deprecated")
DEFAULT_STATUS = "stable"


def is_human_actor(actor: str) -> bool:
    """True for a ``human:<id>`` actor (§7). Consumers key trust off this."""
    return isinstance(actor, str) and actor.startswith("human:")


def verifications(data: dict) -> list[dict]:
    """The concept's ``verified`` events as a list of ``{by, at}`` dicts.

    A bare mapping is one event (§5.2's MUST); a list passes through;
    anything else (absent, scalar junk) is no events. Non-dict list entries
    are dropped rather than raised — permissive consumption (§11).
    """
    v = data.get("verified")
    if isinstance(v, dict):
        return [v]
    if isinstance(v, list):
        return [e for e in v if isinstance(e, dict)]
    return []


def trust_tier(data: dict) -> str:
    """Derive the §5.3 trust tier from the ``verified`` family."""
    events = verifications(data)
    if not events:
        return UNVERIFIED
    if any(is_human_actor(e.get("by", "")) for e in events):
        return HUMAN_REVIEWED
    return MACHINE_CONFIRMED


def effective_status(data: dict) -> str:
    """``status`` with the spec default: absent or unknown ⇒ ``stable``."""
    s = data.get("status")
    return s if s in STATUSES else DEFAULT_STATUS


def _as_date(value) -> dt.date | None:
    """Coerce a YYYY-MM-DD string / date / datetime to a date, else None."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def is_stale(data: dict, today: dt.date | None = None) -> bool:
    """True when ``today >= stale_after`` (§5.5). No ``stale_after`` ⇒ False."""
    after = _as_date(data.get("stale_after"))
    if after is None:
        return False
    return (today or dt.date.today()) >= after


def generated_at(data: dict) -> str | None:
    """When the content last meaningfully changed.

    ``generated.at`` when present. The superseded v0.1 ``timestamp`` is
    consulted **only when ``generated`` is absent** — §13.1 licenses the
    fallback for absence alone, so a ``generated`` that carries no ``at``
    (legal: only ``by`` is required) yields None rather than an unrelated
    legacy timestamp. Returned as the ISO string the frontmatter carries.
    """
    gen = data.get("generated")
    if gen is not None:
        at = gen.get("at") if isinstance(gen, dict) else None
        return str(at) if at else None
    ts = data.get("timestamp")
    return str(ts) if ts else None


def revised_at(data: dict) -> str | None:
    """``revised.at``: the latest in-place edit, when the producer keeps
    ``generated`` as the production event and records edits apart from it
    (LOKF ``revised``, open-knowledge-format#28). None when absent, or when
    the event carries no ``at``."""
    rev = data.get("revised")
    at = rev.get("at") if isinstance(rev, dict) else None
    return str(at) if at else None


def last_changed_at(data: dict) -> str | None:
    """When the content last meaningfully changed: the later of
    :func:`revised_at` and :func:`generated_at`, as the ISO string the
    frontmatter carries.

    A producer that restamps ``generated.at`` on each edit writes no
    ``revised``; one that keeps ``generated`` as the production event
    writes ``revised`` on each edit. Both read the same way here. A time
    that does not parse yields to the other; when neither parses, the
    first present is returned as it is, as :func:`generated_at` does.
    """
    present = [(t, _as_datetime(t)) for t in (revised_at(data), generated_at(data)) if t]
    dated = [(t, d) for t, d in present if d is not None]
    if dated:
        return max(dated, key=lambda td: td[1])[0]
    return present[0][0] if present else None


def _as_datetime(value) -> dt.datetime | None:
    """Read an ISO timestamp in UTC; dates and naive times use UTC."""
    try:
        if isinstance(value, dt.datetime):
            parsed = value
        elif isinstance(value, dt.date):
            parsed = dt.datetime.combine(value, dt.time())
        elif isinstance(value, str):
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return None
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)
    except (ValueError, OverflowError):
        return None


def human_reviewed_at(data: dict) -> str | None:
    """Latest valid human review timestamp, normalized to UTC."""
    times = [
        at for event in verifications(data)
        if is_human_actor(event.get("by"))
        if (at := _as_datetime(event.get("at"))) is not None
    ]
    return max(times).isoformat().replace("+00:00", "Z") if times else None


def edited_since_human_review(data: dict) -> bool:
    """Whether a meaningful edit follows the latest dated human review.

    The edit is :func:`last_changed_at`, so a producer that writes ``revised``
    and one that restamps ``generated.at`` are read alike. Missing or
    malformed timestamps mean unknown (False), not unchanged. Review revision
    identifiers do not alter this timestamp comparison.
    """
    changed = _as_datetime(last_changed_at(data))
    reviewed = _as_datetime(human_reviewed_at(data))
    return changed > reviewed if changed is not None and reviewed is not None else False


def trust_summary(data: dict, today: dt.date | None = None) -> dict:
    """All derived signals in one dict — the shape consumer surfaces show."""
    return {
        "trust_tier": trust_tier(data),
        "status": effective_status(data),
        "stale": is_stale(data, today),
        "generated_at": generated_at(data),
        "revised_at": revised_at(data),
        "last_changed_at": last_changed_at(data),
        "verified_count": len(verifications(data)),
        "human_reviewed_at": human_reviewed_at(data),
        "edited_since_human_review": edited_since_human_review(data),
    }
