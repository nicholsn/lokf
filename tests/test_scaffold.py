"""`lokf new` — scaffold a publishable knowledge-base repo."""
import pytest

from lokf import rdf, scaffold
from lokf.model import load_bundle


def test_scaffold_writes_the_repo(tmp_path):
    root = scaffold.new("my-kb", path=tmp_path, base_iri="https://ex.org/my-kb/")
    for rel in [
        "knowledge/index.md",
        "knowledge/glossary/active-user.md",
        "knowledge/metrics/weekly-active-users.md",
        "mkdocs.yml",
        ".github/workflows/pages.yml",
        "justfile",
        "README.md",
        ".gitignore",
    ]:
        assert (root / rel).exists(), rel
    # the bundled agent skills are copied in, including this one
    assert (root / ".claude/skills/author-concept/SKILL.md").exists()
    assert (root / ".claude/skills/scaffold-knowledge-base/SKILL.md").exists()


def test_scaffolded_bundle_is_valid_lokf(tmp_path):
    root = scaffold.new("kb", path=tmp_path, base_iri="https://ex.org/kb/")
    bundle = load_bundle(root / "knowledge")
    assert len(bundle.concepts) == 2
    # it projects to RDF, and the example `measures` edge is present
    ttl = rdf.serialize(root / "knowledge", "ttl").lower()
    assert "weekly active users" in ttl
    assert "measures" in ttl


def test_title_and_base_iri_defaults(tmp_path):
    root = scaffold.new("cool-kb", path=tmp_path)
    index = (root / "knowledge/index.md").read_text()
    assert "https://example.org/cool-kb/" in index
    assert "Cool Kb" in index  # title derived from the name


def test_refuses_nonempty_target(tmp_path):
    (tmp_path / "kb").mkdir()
    (tmp_path / "kb" / "keep.md").write_text("x")
    with pytest.raises(FileExistsError):
        scaffold.new("kb", path=tmp_path)
