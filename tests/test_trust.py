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
        "revised_at": None,
        "last_changed_at": AGENT["at"],
        "verified_count": 1,
        "human_reviewed_at": HUMAN["at"],
        "edited_since_human_review": False,
        "refuted": False,
        "refuted_at": None,
    }


# -- refuted: a no beside the yes ---------------------------------------------
NO = {"by": "human:ada", "at": "2026-07-01T00:00:00Z", "reason": "the figure is from the old report"}


def test_refuted_normalizes_as_verified_does():
    assert trust.refutations({"refuted": NO}) == [NO]
    assert trust.refutations({"refuted": [NO, "junk"]}) == [NO]
    assert trust.refutations({}) == [] and trust.refutations({"refuted": "no"}) == []


def test_a_refutation_is_active_until_a_later_edit():
    data = {"generated": AGENT, "verified": [HUMAN], "refuted": [NO]}
    assert trust.active_refutations(data) == [NO]
    assert trust.refuted_at(data) == NO["at"]
    s = trust.trust_summary(data)
    assert s["refuted"] is True and s["refuted_at"] == NO["at"]
    # The tier is OKF's, from verified alone; the no sits beside it.
    assert s["trust_tier"] == "human-reviewed"
    # An edit after the refutation leaves it as history, through either event.
    assert not trust.active_refutations({**data, "revised": {"by": "process:x", "at": "2026-07-02"}})
    assert not trust.active_refutations({**data, "generated": {"by": "process:x", "at": "2026-07-02"}})
    # An edit at the same instant does not resolve it; neither does an undated one.
    assert trust.active_refutations({**data, "revised": {"by": "process:x", "at": NO["at"]}}) == [NO]
    assert trust.active_refutations({**data, "generated": {"by": "process:x"}}) == [NO]
    undated = {"by": "human:ada", "reason": "wrong"}
    assert trust.active_refutations({"generated": AGENT, "refuted": undated}) == [undated]
    assert trust.refuted_at({"generated": AGENT, "refuted": undated}) is None


# -- revised: the last edit apart from an immutable generated ---------------
def test_last_change_is_the_later_of_revised_and_generated():
    edited = {"generated": AGENT, "revised": {"by": "human:x", "at": "2026-07-01T00:00:00Z"}}
    assert trust.revised_at(edited) == "2026-07-01T00:00:00Z"
    assert trust.last_changed_at(edited) == "2026-07-01T00:00:00Z"
    # A producer that restamps generated.at instead writes no revised.
    assert trust.revised_at({"generated": AGENT}) is None
    assert trust.last_changed_at({"generated": AGENT}) == AGENT["at"]
    # generated_at itself is untouched: it is the production event.
    assert trust.generated_at(edited) == AGENT["at"]
    # The legacy timestamp is a last change too, when generated is absent.
    assert trust.last_changed_at({"timestamp": "2020-01-01T00:00:00Z"}) == "2020-01-01T00:00:00Z"
    assert trust.last_changed_at({}) is None


def test_last_change_tolerates_a_malformed_or_undated_event():
    assert trust.last_changed_at({"generated": AGENT, "revised": {"by": "human:x"}}) == AGENT["at"]
    assert trust.last_changed_at({"generated": AGENT, "revised": {"by": "human:x", "at": "bad"}}) == AGENT["at"]
    assert trust.last_changed_at({"generated": {"by": "human:x", "at": "bad"},
                                  "revised": {"by": "human:x", "at": "2026-07-01"}}) == "2026-07-01"
    assert trust.last_changed_at({"generated": {"by": "human:x", "at": "bad"}}) == "bad"
    assert trust.last_changed_at({"revised": "junk", "generated": AGENT}) == AGENT["at"]


def test_edited_since_review_reads_revised():
    reviewed = {"generated": AGENT, "verified": [HUMAN]}
    assert not trust.edited_since_human_review(reviewed)
    reviewed["revised"] = {"by": "process:librarian", "at": "2026-06-26T00:00:00Z"}
    assert trust.edited_since_human_review(reviewed)
    assert trust.trust_summary(reviewed)["last_changed_at"] == "2026-06-26T00:00:00Z"
    assert trust.trust_summary(reviewed)["trust_tier"] == "human-reviewed"


# -- OKF spaced-type alias (v0.2 §10 writes 'Attested Computation') ----------
def test_spaced_okf_type_normalizes(tmp_path):
    from lokf.parse import parse_concept

    p = tmp_path / "c.md"
    p.write_text(
        "---\ntype: Attested Computation\ntitle: X\nruntime: bigquery\n---\nbody\n",
        encoding="utf-8",
    )
    assert parse_concept(str(p))["type"] == "AttestedComputation"


def test_review_freshness_normalizes_and_selects_latest():
    data = {"generated": {"at": "2026-06-25T14:00:01Z"}, "verified": [
        {"by": "human:a", "at": "2026-06-25"},
        {"by": "human:b", "at": "2026-06-25T10:00:00-04:00", "revision": "old"},
        {"by": "human:c", "at": "bad"},
        {"by": "process:x", "at": "2027-01-01"},
    ]}
    assert trust.human_reviewed_at(data) == "2026-06-25T14:00:00Z"
    assert trust.edited_since_human_review(data)
    assert trust.trust_tier(data) == "human-reviewed"
    data["verified"].append({"by": "human:d", "at": "2026-06-25T14:00:01Z"})
    assert not trust.edited_since_human_review(data)


def test_review_freshness_missing_malformed_and_legacy():
    for data in [{}, {"verified": HUMAN}, {"generated": {"at": "bad"}, "verified": HUMAN},
                 {"generated": {"at": "2027-01-01"}, "verified": {"by": "human:a", "at": "bad"}}]:
        assert not trust.edited_since_human_review(data)
    assert trust.edited_since_human_review({"timestamp": "2027-01-01", "verified": HUMAN})
    assert not trust.edited_since_human_review({"generated": {}, "timestamp": "2027-01-01", "verified": HUMAN})
    assert trust.human_reviewed_at({"verified": {"by": "human:a", "at": dt.date(2026, 1, 1)}}) == "2026-01-01T00:00:00Z"
