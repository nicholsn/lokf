"""Where a concept's frontmatter block opens and closes."""
from __future__ import annotations

import pytest

import lokf
from lokf.agentskills import _frontmatter
from lokf.parse import parse_concept, parse_concept_text, parse_index_text, split_frontmatter

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


def test_blank_lines_before_the_block_are_returned_for_a_rewriter():
    lead, front, body = split_frontmatter("\n\n---\ntype: Service\n---\n\nThe body.\n")
    assert lead == "\n\n"
    assert front == "\ntype: Service\n"
    assert body == "\n\nThe body.\n"


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("<!-- reviewed -->\n\n---\ntype: Service\n---\n\nBody.\n", id="a comment"),
        pytest.param("Title\n---\ntype: Service\n---\nBody.\n", id="a heading underlined with dashes"),
        pytest.param("Prose.\n\n```yaml\n---\ntype: Service\n---\n```\n", id="a fenced example"),
        pytest.param(
            f"<!--\n---\ntype: Service\n{EVENT}---\n-->\n---\ntype: Service\n---\n\nBody.\n",
            id="a block hidden in a comment",
        ),
    ],
)
def test_text_before_the_block_means_no_block(raw):
    assert split_frontmatter(raw) is None
    with pytest.raises(ValueError, match="x.md: no YAML frontmatter .* at the top of the file"):
        parse_concept_text(raw, "x.md")


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("--- \ntype: Service\n---  \nBody.\n", id="a space after each delimiter"),
        pytest.param("---\t\ntype: Service\n---\t\nBody.\n", id="a tab after each delimiter"),
        pytest.param("---\r\ntype: Service\r\n---\r\nBody.\r\n", id="CRLF line endings"),
        pytest.param("---\rtype: Service\r---\rBody.\r", id="carriage returns alone"),
        pytest.param("\ufeff---\ntype: Service\n---\nBody.\n", id="a byte order mark"),
        pytest.param("\n---\ntype: Service\n---\nBody.\n", id="a blank line first"),
        pytest.param("---\ntype: Service\n---", id="no body"),
    ],
)
def test_the_block_opens_and_closes_as_it_did(raw):
    assert parse_concept_text(raw)["type"] == "Service"


def test_a_rewriter_gets_the_byte_order_mark_back():
    assert split_frontmatter("\ufeff---\ntype: Service\n---\n")[0] == "\ufeff"


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("# A page\n", id="no delimiter"),
        pytest.param("---\ntype: Service\n\nBody.\n", id="no closing delimiter"),
        pytest.param("---\ntype: Service\ntitle: a---b\n", id="a closing delimiter only inside a value"),
        pytest.param("A page---with dashes---here\n", id="an opening delimiter only inside a line"),
        pytest.param("  ---\ntype: Service\n  ---\nBody.\n", id="delimiters that are indented"),
        pytest.param("--- x\ntype: Service\n--- y\nBody.\n", id="delimiters with text after them"),
        pytest.param("---\nsearch: 1\n---# Type: Time\n", id="a closing delimiter glued to text"),
    ],
)
def test_no_block_is_a_clear_error(raw):
    assert split_frontmatter(raw) is None
    with pytest.raises(ValueError, match="x.md: no YAML frontmatter .* on a line of its own"):
        parse_concept_text(raw, "x.md")


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        pytest.param("---\n- a\n- b\n---\nBody.\n", "must be a mapping, not list", id="a list"),
        pytest.param("---\nSome text\n---\nBody.\n", "must be a mapping, not str", id="text"),
        pytest.param("---\ntype: [\n---\nBody.\n", "not valid YAML", id="broken YAML"),
        pytest.param(
            "---\ntype: Service\n--- # note\n\nBody.\n\n---\n\nMore.\n",
            "not valid YAML",
            id="a closer with a comment and a rule further down",
        ),
    ],
)
def test_frontmatter_that_cannot_be_read_names_the_file(raw, message):
    with pytest.raises(ValueError, match=f"x.md: .*{message}"):
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


META = "base_iri: https://example.invalid/k/\n"


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(f"---\n{META}---\n\n# Index\n", id="at the top"),
        pytest.param(f"\ufeff---\n{META}---\n\n# Index\n", id="after a byte order mark"),
        pytest.param(f"\n---\n{META}---\n\n# Index\n", id="after a blank line"),
    ],
)
def test_an_index_block_at_the_top_is_read(raw):
    assert parse_index_text(raw)["base_iri"] == "https://example.invalid/k/"


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("# Index\n", id="no dashes"),
        pytest.param("# Index\n\n---\n\ntitle: not meta\n\n---\n", id="rules lower down"),
        pytest.param("----\n\n# Index\n", id="a rule of four dashes first"),
        pytest.param(f"<!-- c -->\n---\n{META}---\n", id="a block after other text"),
    ],
)
def test_an_index_with_no_block_at_the_top_has_no_metadata(raw):
    assert parse_index_text(raw) == {}


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(f"---\n{META}\n# Index\n", id="no closing delimiter"),
        pytest.param(f"---\n{META}--- x\n# Index\n", id="text after the closing delimiter"),
        pytest.param(f"--- x\n{META}---\n# Index\n", id="text after the opening delimiter"),
        pytest.param(f"--- x\n{META}---\n# Index\n\n---\n", id="text after the opening delimiter and a rule below"),
    ],
)
def test_an_index_that_does_not_close_its_block_is_an_error(raw, tmp_path):
    (tmp_path / "index.md").write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="index.md: frontmatter is not closed"):
        lokf.load_bundle(tmp_path)


def test_a_skill_page_with_no_block_has_no_frontmatter(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text("# A skill\n", encoding="utf-8")
    assert _frontmatter(path) == {}


def test_a_skill_page_keeps_its_whole_block(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: x\ndescription: Before---after\nlicense: MIT\n---\n\nBody.\n", encoding="utf-8")
    assert _frontmatter(path) == {"name": "x", "description": "Before---after", "license": "MIT"}
