"""`lokf new` — scaffold a publishable knowledge-base repo (Astro + graph browser)."""
import pytest

from lokf import rdf, scaffold
from lokf.model import load_bundle


def test_scaffold_writes_the_repo(tmp_path):
    root = scaffold.new("my-kb", path=tmp_path, base_iri="https://ex.org/my-kb/")
    for rel in [
        "knowledge/index.md",
        "knowledge/glossary/active-user.md",
        "knowledge/metrics/weekly-active-users.md",
        "package.json",
        "astro.config.mjs",
        "tsconfig.json",
        "src/content.config.ts",
        "src/lib/lokf.ts",
        "src/layouts/Base.astro",
        "src/pages/index.astro",
        "src/pages/[...slug].astro",
        "src/pages/graph.astro",
        "src/pages/graph.json.ts",
        "src/pages/graph.jsonld.ts",
        ".github/workflows/pages.yml",
        ".gitignore",
        "justfile",
        "README.md",
    ]:
        assert (root / rel).exists(), rel
    # the bundled agent skills are copied in, including the scaffolding one
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


def test_tokens_substituted_everywhere(tmp_path):
    root = scaffold.new(
        "kb", path=tmp_path, title="My KB", base_iri="https://org.github.io/kb/"
    )
    leftovers = [
        p for p in root.rglob("*")
        if p.is_file() and ".claude" not in p.parts and "__KB_" in p.read_text()
    ]
    assert leftovers == []
    # site/base derived from the base IRI (a GitHub *project* page here)
    config = (root / "astro.config.mjs").read_text()
    assert "site: 'https://org.github.io'" in config
    assert "base: '/kb'" in config
    assert "'__KB_BASE_IRI__glossary" not in (root / "knowledge/metrics/weekly-active-users.md").read_text()
    assert "https://org.github.io/kb/glossary/active-user" in (
        root / "knowledge/metrics/weekly-active-users.md"
    ).read_text()


def test_root_domain_base_iri(tmp_path):
    root = scaffold.new("kb", path=tmp_path, base_iri="https://kb.example.com/")
    config = (root / "astro.config.mjs").read_text()
    assert "site: 'https://kb.example.com'" in config
    assert "base: '/'" in config


def test_title_and_base_iri_defaults(tmp_path):
    root = scaffold.new("cool-kb", path=tmp_path)
    index = (root / "knowledge/index.md").read_text()
    assert "https://example.org/cool-kb/" in index
    assert "Cool Kb" in index  # title derived from the name
    assert '"name": "cool-kb"' in (root / "package.json").read_text()


def test_refuses_nonempty_target(tmp_path):
    (tmp_path / "kb").mkdir()
    (tmp_path / "kb" / "keep.md").write_text("x")
    with pytest.raises(FileExistsError):
        scaffold.new("kb", path=tmp_path)


def test_refuses_file_target(tmp_path):
    (tmp_path / "kb").write_text("i am a file")
    with pytest.raises(FileExistsError):
        scaffold.new("kb", path=tmp_path)
