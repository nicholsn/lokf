"""Link extraction, relation proposals, and apply() against the reference bundle."""
import json
import pathlib
import shutil

import pytest

import lokf
from lokf.cli import main
from lokf.model import Concept
from lokf.propose import CUE_TABLE, UNCUED, Link, Proposal, apply, extract_links, propose

BUNDLE = pathlib.Path(__file__).parent.parent / "examples" / "acme-knowledge"
WAU_IRI = "https://acme.example/knowledge/metrics/weekly-active-users"


@pytest.fixture(scope="module")
def bundle():
    return lokf.load_bundle(BUNDLE)


@pytest.fixture(scope="module")
def vocab():
    return lokf.vocabulary()


def _fake(concept_id: str, body: str, type_: str = "Document") -> Concept:
    return Concept(
        path=BUNDLE / (concept_id + ".md"),
        data={"type": type_, "body": body},
        concept_id=concept_id,
    )


def test_extract_links_finds_prose_links(bundle):
    term = bundle.get("glossary/active-user")
    links = extract_links(term, bundle)
    assert len(links) == 1
    link = links[0]
    assert link.text == "Weekly Active Users"
    assert link.target_raw == "/metrics/weekly-active-users.md"
    assert link.target is bundle.get("metrics/weekly-active-users")
    assert "Used by" in link.sentence


def test_extract_links_excludes_code(bundle):
    body = (
        "See [Events](/datasets/events.md) for context.\n\n"
        "```md\n"
        "[User Events](/tables/user-events.md)\n"
        "```\n\n"
        "And an inline `[WAU](/metrics/weekly-active-users.md)` span.\n"
    )
    links = extract_links(_fake("notes/fake", body), bundle)
    assert [link.text for link in links] == ["Events"]


def test_extract_links_title_and_angle_targets(bundle):
    body = (
        'See [Events](/datasets/events.md "Event stream docs") and '
        "[WAU](</metrics/weekly-active-users.md>)."
    )
    links = extract_links(_fake("notes/fake", body), bundle)
    assert [link.target_raw for link in links] == [
        "/datasets/events.md",
        "/metrics/weekly-active-users.md",
    ]
    assert links[0].target is bundle.get("datasets/events")
    assert links[1].target is bundle.get("metrics/weekly-active-users")


def test_extract_links_relative_and_unresolved(bundle):
    body = (
        "Counts each [active user](../glossary/active-user.md); "
        "see the [RFC](https://wiki.acme.example/rfc/metric-defs)."
    )
    links = extract_links(_fake("metrics/fake", body), bundle)
    assert len(links) == 2
    assert links[0].target is bundle.get("glossary/active-user")
    assert links[1].target is None  # not a bundle concept, still returned


def test_propose_skips_asserted_and_proposes_active_user_link(bundle, vocab):
    proposals = propose(bundle, vocab)
    # WAU's body links are already dependsOn/derivedFrom, user-events' link is
    # already isPartOf, and every other body link is asserted too — the only
    # survivor is glossary/active-user -> WAU.
    assert len(proposals) == 1
    p = proposals[0]
    assert p.source.concept_id == "glossary/active-user"
    assert p.link.target.concept_id == "metrics/weekly-active-users"
    assert p.relation.name in ("references", "relatedTo")
    assert 0.0 < p.confidence <= 1.0
    # target_iri is resolved at propose() time and is what apply() writes.
    assert p.target_iri == WAU_IRI
    assert p.target_iri == bundle.iri(p.link.target)


def test_every_relation_type_cued_or_uncued(vocab):
    """Each RelationType is reachable from a cue, or explicitly UNCUED."""
    cued = {name for _, name, _ in CUE_TABLE}
    for name in vocab.relation_types:
        assert name in cued or name in UNCUED, (
            f"{name} has no CUE_TABLE entry and is not listed in UNCUED"
        )
    assert UNCUED <= set(vocab.relation_types)


def test_propose_respects_measures_domain(bundle, vocab):
    body = "This counts [Active User](/glossary/active-user.md) sessions."
    [mp] = propose(bundle, vocab, concept=_fake("metrics/fake", body, "Metric"))
    assert mp.relation.name == "measures"
    [tp] = propose(bundle, vocab, concept=_fake("tables/fake", body, "Table"))
    assert tp.relation.name == "relatedTo"  # measures excluded, fallback


@pytest.fixture()
def tmp_bundle(tmp_path):
    root = tmp_path / "acme-knowledge"
    shutil.copytree(BUNDLE, root)
    # Inject a frontmatter comment to prove round-trip preservation.
    term = root / "glossary" / "active-user.md"
    term.write_text(
        term.read_text(encoding="utf-8").replace(
            "tags: [glossary]", "tags: [glossary] # taxonomy tags"
        ),
        encoding="utf-8",
    )
    return root


def test_apply_writes_slot_and_preserves_formatting(tmp_bundle, vocab):
    bundle = lokf.load_bundle(tmp_bundle)
    proposals = propose(bundle, vocab)
    assert len(proposals) == 1

    term = tmp_bundle / "glossary" / "active-user.md"
    before = term.read_text(encoding="utf-8")
    applied = apply(proposals)
    assert applied == proposals

    after = term.read_text(encoding="utf-8")
    assert "# taxonomy tags" in after  # comment intact
    assert "timestamp: 2026-03-01T00:00:00Z" in after  # scalar formatting intact
    assert f"{proposals[0].relation.name}:" in after
    assert WAU_IRI in after
    assert after.split("---", 2)[2] == before.split("---", 2)[2]  # body untouched

    # Re-running propose on the updated bundle skips the now-asserted link.
    assert propose(lokf.load_bundle(tmp_bundle), vocab) == []
    # Re-applying the stale proposals writes nothing new.
    assert apply(proposals) == []
    assert term.read_text(encoding="utf-8") == after


def test_apply_preserves_preamble(tmp_bundle, vocab):
    term = tmp_bundle / "glossary" / "active-user.md"
    preamble = "<!-- reviewed: 2026-07-01 -->\n\n"
    term.write_text(preamble + term.read_text(encoding="utf-8"), encoding="utf-8")
    before = term.read_text(encoding="utf-8")

    bundle = lokf.load_bundle(tmp_bundle)
    proposals = propose(bundle, vocab)
    assert len(proposals) == 1
    assert apply(proposals) == proposals

    after = term.read_text(encoding="utf-8")
    assert WAU_IRI in after
    # Preamble (before the first ---) and body (after the second) are
    # preserved byte-for-byte; only the frontmatter block changed.
    assert after.split("---", 2)[0] == preamble
    assert after.split("---", 2)[2] == before.split("---", 2)[2]


def test_apply_empty_frontmatter(tmp_bundle, vocab):
    notes = tmp_bundle / "notes"
    notes.mkdir()
    scratch = notes / "scratch.md"
    scratch.write_text(
        "---\n---\n\nSee [Events](/datasets/events.md).\n", encoding="utf-8"
    )
    bundle = lokf.load_bundle(tmp_bundle)
    [p] = propose(bundle, vocab, concept=bundle.get("notes/scratch"))
    assert p.relation.name == "references"
    assert apply([p]) == [p]
    data = lokf.parse.parse_concept(str(scratch))
    assert data["references"] == [bundle.iri(bundle.get("datasets/events"))]
    assert data["body"] == "See [Events](/datasets/events.md)."


def test_apply_min_confidence_filters(tmp_bundle, vocab):
    bundle = lokf.load_bundle(tmp_bundle)
    proposals = propose(bundle, vocab)
    before = (tmp_bundle / "glossary" / "active-user.md").read_text(encoding="utf-8")
    assert apply(proposals, min_confidence=0.99) == []
    after = (tmp_bundle / "glossary" / "active-user.md").read_text(encoding="utf-8")
    assert after == before


def test_apply_reified_relation(tmp_bundle, vocab):
    relation = vocab.relation_types["joinsWith"]
    assert not relation.is_slot
    bundle = lokf.load_bundle(tmp_bundle)
    source = bundle.get("tables/user-events")
    target = bundle.get("datasets/events")
    link = Link(
        text="Events",
        target_raw="/datasets/events.md",
        target=target,
        sentence="joins with Events",
    )
    proposal = Proposal(
        source=source,
        link=link,
        relation=relation,
        confidence=0.9,
        rationale="manual",
        target_iri=bundle.iri(target),
    )
    assert apply([proposal]) == [proposal]
    data = lokf.parse.parse_concept(str(source.path))
    assert data["relations"] == [
        {"predicate": "joinsWith", "target": bundle.iri(target)}
    ]
    assert apply([proposal]) == []  # no duplicate on re-apply
    assert lokf.parse.parse_concept(str(source.path))["relations"] == data["relations"]


def test_joins_with_cue_reaches_reified_apply(tmp_bundle, vocab):
    """A prose 'joins with' link classifies to joinsWith and applies reified."""
    sessions = tmp_bundle / "tables" / "sessions.md"
    sessions.write_text(
        "---\ntype: Table\ntitle: Sessions\n---\n\n"
        "Each row joins with [User Events](/tables/user-events.md) on `user_id`.\n",
        encoding="utf-8",
    )
    bundle = lokf.load_bundle(tmp_bundle)
    [p] = propose(bundle, vocab, concept=bundle.get("tables/sessions"))
    assert p.relation.name == "joinsWith"
    assert not p.relation.is_slot
    assert p.target_iri == bundle.iri(bundle.get("tables/user-events"))
    assert apply([p]) == [p]
    data = lokf.parse.parse_concept(str(sessions))
    assert data["relations"] == [
        {"predicate": "joinsWith", "target": p.target_iri}
    ]


def test_cli_json_apply_composes(tmp_bundle, capsys):
    term = tmp_bundle / "glossary" / "active-user.md"
    before = term.read_text(encoding="utf-8")

    # --json alone is a dry run: no "applied" key, nothing written.
    assert main(["propose", str(tmp_bundle), "--json"]) == 0
    [row] = json.loads(capsys.readouterr().out)
    assert "applied" not in row
    assert term.read_text(encoding="utf-8") == before

    # --json --apply composes: files are written AND the JSON reports it.
    assert main(["propose", str(tmp_bundle), "--json", "--apply"]) == 0
    [row] = json.loads(capsys.readouterr().out)
    assert row["applied"] is True
    assert row["target"] == WAU_IRI
    after = term.read_text(encoding="utf-8")
    assert WAU_IRI in after
    assert f"{row['predicate']}:" in after

    # Re-running finds nothing left to propose.
    assert main(["propose", str(tmp_bundle), "--json", "--apply"]) == 0
    assert json.loads(capsys.readouterr().out) == []
