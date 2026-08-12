"""Tests for consumer-side OKF v0.2 trust semantics (lokf.trust)."""
from __future__ import annotations

import datetime as dt

from lokf import trust

HUMAN = {"by": "human:ahormati", "at": "2026-06-25T09:00:00Z"}
PROCESS = {"by": "process:finance-nightly", "at": "2026-06-26T02:00:00Z"}
AGENT = {"by": "reference_agent/gemini-2.5-pro", "at": "2026-06-20T22:53:05Z"}


# -- verified normalization (§5.2 MUST) --------------------------------------
def test_bare_verified_mapping_is_one_element_list():
    assert trust.verifications({"verified": HUMAN}) == [HUMAN]


def test_verified_list_passes_through_dropping_junk():
    assert trust.verifications({"verified": [HUMAN, "junk", PROCESS]}) == [HUMAN, PROCESS]


def test_verified_absent_or_scalar_is_empty():
    assert trust.verifications({}) == []
    assert trust.verifications({"verified": "yes"}) == []


# -- trust tiers (§5.3) ------------------------------------------------------
def test_tiers():
    assert trust.trust_tier({}) == "unverified"
    assert trust.trust_tier({"verified": [PROCESS, AGENT]}) == "machine-confirmed"
    assert trust.trust_tier({"verified": [PROCESS, HUMAN]}) == "human-reviewed"
    # bare mapping goes through normalization
    assert trust.trust_tier({"verified": HUMAN}) == "human-reviewed"


def test_actor_convention_only_human_prefix_counts():
    # 'team:' and producer/version actors are non-human (§7)
    assert not trust.is_human_actor("team:finance-fpa")
    assert not trust.is_human_actor("reference_agent/gemini-2.5-pro")
    assert trust.is_human_actor("human:kliu@acme")


# -- status (§5.4) -----------------------------------------------------------
def test_status_default_and_passthrough():
    assert trust.effective_status({}) == "stable"
    assert trust.effective_status({"status": "draft"}) == "draft"
    assert trust.effective_status({"status": "deprecated"}) == "deprecated"
    assert trust.effective_status({"status": "bogus"}) == "stable"  # permissive


# -- staleness (§5.5) --------------------------------------------------------
def test_stale_is_plain_date_comparison():
    d = {"stale_after": "2026-06-15"}
    assert not trust.is_stale(d, today=dt.date(2026, 6, 14))
    assert trust.is_stale(d, today=dt.date(2026, 6, 15))  # on the day: stale
    assert trust.is_stale(d, today=dt.date(2026, 7, 1))
    assert not trust.is_stale({}, today=dt.date(2026, 7, 1))


def test_stale_accepts_parsed_date_objects():
    # yaml.safe_load gives datetime.date for unquoted dates; isoify may stringify
    assert trust.is_stale({"stale_after": dt.date(2026, 1, 1)}, today=dt.date(2026, 1, 1))
    assert not trust.is_stale({"stale_after": "not-a-date"}, today=dt.date(2026, 1, 1))


# -- generated.at with timestamp fallback (§13.1) ----------------------------
def test_generated_at_prefers_generated_then_timestamp():
    both = {"generated": AGENT, "timestamp": "2020-01-01T00:00:00Z"}
    assert trust.generated_at(both) == AGENT["at"]
    assert trust.generated_at({"timestamp": "2020-01-01T00:00:00Z"}) == "2020-01-01T00:00:00Z"
    assert trust.generated_at({}) is None


def test_generated_present_without_at_blocks_timestamp_fallback():
    """§13.1: the timestamp fallback applies only when `generated` is ABSENT."""
    d = {"generated": {"by": "human:x"}, "timestamp": "2020-01-01T00:00:00Z"}
    assert trust.generated_at(d) is None
    # malformed-but-present generated is likewise not "absent"
    assert trust.generated_at({"generated": "oops", "timestamp": "2020-01-01T00:00:00Z"}) is None


# -- summary shape -----------------------------------------------------------
def test_trust_summary_shape():
    s = trust.trust_summary(
        {"verified": HUMAN, "status": "stable", "stale_after": "2026-06-15", "generated": AGENT},
        today=dt.date(2026, 7, 1),
    )
    assert s == {
        "trust_tier": "human-reviewed",
        "status": "stable",
        "stale": True,
        "generated_at": AGENT["at"],
        "verified_count": 1,
    }


# -- OKF spaced-type alias (v0.2 §10 writes 'Attested Computation') ----------
def test_spaced_okf_type_normalizes(tmp_path):
    from lokf.parse import parse_concept

    p = tmp_path / "c.md"
    p.write_text(
        "---\ntype: Attested Computation\ntitle: X\nruntime: bigquery\n---\nbody\n",
        encoding="utf-8",
    )
    assert parse_concept(str(p))["type"] == "AttestedComputation"
