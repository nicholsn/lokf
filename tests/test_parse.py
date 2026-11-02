"""Where a concept's frontmatter block opens and closes."""
from __future__ import annotations

import pytest

import lokf
from lokf.agentskills import _frontmatter
from lokf.parse import parse_concept, parse_concept_text, split_frontmatter

EVENT = 'verified:\n  - by: human:ada\n    at: "2026-01-02T10:00:00Z"\n'


@pytest.mark.parametrize(
    "value",
    ["Before---after", "a --- b", "---dashes", "dashes---", "Under ---- four"],
    ids=["inside a word", "between spaces", "at the start", "at the end", "four dashes"],
)
def test_dashes_inside_a_value_do_not_end_the_block(value):
    data = parse_concept_text(f"---\ntype: Service\ntitle: {value}\nresource: docs/a.md\n{EVENT}---\n\nThe body.\n")
    assert data["title"] == value
    assert data["resource"] == "docs/a.md"
    assert data["verified"][0]["by"] == "human:ada"
    assert data["body"] == "The body."


def test_dashes_indented_inside_a_block_scalar_do_not_end_the_block():
    data = parse_concept_text("---\ntype: Service\ndescription: |\n  one\n  ---\n  two\n---\n\nThe body.\n")
    assert data["description"] == "one\n---\ntwo\n"
    assert data["body"] == "The body."


def test_a_rule_in_the_body_stays_in_the_body():
    data = parse_concept_text("---\ntype: Service\n---\n\nOne.\n\n---\n\nTwo.\n\n---\n")
    assert data["body"] == "One.\n\n---\n\nTwo.\n\n---"


def test_the_preamble_before_the_block_is_kept_and_may_hold_dashes():
    raw = "<!-- reviewed---2026-07-01 -->\n\n---\ntype: Service\n---\n\nThe body.\n"
    preamble, front, body = split_frontmatter(raw)
    assert preamble == "<!-- reviewed---2026-07-01 -->\n\n"
    assert front == "\ntype: Service\n"
    assert body == "\n\nThe body.\n"


@pytest.mark.parametrize(
    ("what", "raw"),
    [
        ("a space after each delimiter", "--- \ntype: Service\n---  \nBody.\n"),
        ("a tab after each delimiter", "---\t\ntype: Service\n---\t\nBody.\n"),
        ("CRLF line endings", "---\r\ntype: Service\r\n---\r\nBody.\r\n"),
        ("carriage returns alone", "---\rtype: Service\r---\rBody.\r"),
        ("a byte order mark", "﻿---\ntype: Service\n---\nBody.\n"),
        ("a blank line first", "\n---\ntype: Service\n---\nBody.\n"),
        ("no body", "---\ntype: Service\n---"),
    ],
    ids=lambda value: value if " " in value and "---" not in value else "",
)
def test_the_block_opens_and_closes_as_it_did(what, raw):
    assert parse_concept_text(raw)["type"] == "Service", what


def test_a_rewriter_gets_the_byte_order_mark_back_in_the_preamble():
    assert split_frontmatter("﻿---\ntype: Service\n---\n")[0] == "﻿"


@pytest.mark.parametrize(
    ("what", "raw"),
    [
        ("no delimiter", "# A page\n"),
        ("no closing delimiter", "---\ntype: Service\n\nBody.\n"),
        ("a closing delimiter only inside a value", "---\ntype: Service\ntitle: a---b\n"),
        ("an opening delimiter only inside a line", "A page---with dashes---here\n"),
        ("delimiters that are indented", "  ---\ntype: Service\n  ---\nBody.\n"),
        ("delimiters with text after them", "--- x\ntype: Service\n--- y\nBody.\n"),
    ],
    ids=lambda value: value if "---" not in value or value.startswith(("a ", "an ", "delimiters")) else "",
)
def test_no_block_is_a_clear_error(what, raw):
    assert split_frontmatter(raw) is None, what
    with pytest.raises(ValueError, match="no YAML frontmatter"):
        parse_concept_text(raw, "x.md")


def test_a_concept_read_from_a_file_keeps_its_whole_block(tmp_path):
    path = tmp_path / "a.md"
    path.write_text(f"---\ntype: Service\ntitle: Before---after\n{EVENT}---\n\nThe body.\n", encoding="utf-8")
    assert parse_concept(str(path))["verified"][0]["by"] == "human:ada"


def test_the_bundle_index_keeps_its_whole_block(tmp_path):
    (tmp_path / "index.md").write_text(
        "---\ntitle: Before---after\nbase_iri: https://example.invalid/k/\n---\n\n# Index\n", encoding="utf-8"
    )
    bundle = lokf.load_bundle(tmp_path)
    assert bundle.meta["title"] == "Before---after"
    assert bundle.meta["base_iri"] == "https://example.invalid/k/"


def test_a_skill_page_keeps_its_whole_block(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: x\ndescription: Before---after\nlicense: MIT\n---\n\nBody.\n", encoding="utf-8")
    assert _frontmatter(path) == {"name": "x", "description": "Before---after", "license": "MIT"}
