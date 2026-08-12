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


def trust_summary(data: dict, today: dt.date | None = None) -> dict:
    """All derived signals in one dict — the shape consumer surfaces show."""
    return {
        "trust_tier": trust_tier(data),
        "status": effective_status(data),
        "stale": is_stale(data, today),
        "generated_at": generated_at(data),
        "verified_count": len(verifications(data)),
    }
