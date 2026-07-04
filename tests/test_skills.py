"""Packaged agent skills: discovery, frontmatter parsing, and install."""
import yaml

from lokf.agentskills import install, list_skills, skills_dir

SKILL_NAMES = {
    "author-concept",
    "enrich-relations",
    "query-knowledge-base",
    "publish-graph",
    "build-knowledge-base",
    "scaffold-knowledge-base",
}


def test_skills_dir_has_the_bundled_skills():
    root = skills_dir()
    assert root.is_dir()
    dirs = {p.name for p in root.iterdir() if (p / "SKILL.md").is_file()}
    assert dirs == SKILL_NAMES


def test_list_skills_names_match_dirs_and_descriptions_non_empty():
    skills = list_skills()
    assert len(skills) == len(SKILL_NAMES)
    names = {name for name, _ in skills}
    assert names == SKILL_NAMES
    for name, description in skills:
        # The frontmatter name matches its directory, one line, non-empty desc.
        assert (skills_dir() / name / "SKILL.md").is_file()
        assert description.strip()


def test_every_frontmatter_parses():
    for skill in skills_dir().iterdir():
        md = skill / "SKILL.md"
        if not md.is_file():
            continue
        parts = md.read_text(encoding="utf-8").split("---", 2)
        meta = yaml.safe_load(parts[1])
        assert meta["name"] == skill.name
        assert meta["description"].strip()


def test_install_copies_all_skills(tmp_path):
    dest = install(tmp_path / "skills")
    assert dest == tmp_path / "skills"
    copied = sorted(p.parent.name for p in dest.glob("*/SKILL.md"))
    assert copied == sorted(SKILL_NAMES)


def test_install_reruns_without_error(tmp_path):
    dest = tmp_path / "skills"
    install(dest)
    install(dest)  # overwrite same-named skills, no error
    assert sorted(p.parent.name for p in dest.glob("*/SKILL.md")) == sorted(
        SKILL_NAMES
    )
