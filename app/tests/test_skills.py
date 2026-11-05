from den import skills

SKILL = "---\nname: {name}\ndescription: Does {name} things\n---\n# {name}\n"


def write_skill(folder, name, body=None):
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(body or SKILL.format(name=name))


def test_discover_tags_new_identical_and_conflicting_skills(tmp_path, files_root):
    den_skills = files_root / "skills"
    write_skill(den_skills / "same", "same")
    write_skill(den_skills / "changed", "changed")
    source = tmp_path / "source"
    write_skill(source / "skills" / "same", "same")
    write_skill(source / "skills" / "changed", "changed", "---\nname: changed\n---\nnew body\n")
    write_skill(source / "skills" / "fresh", "fresh")
    found = {candidate.name: candidate.status for candidate in skills.discover(source)}
    assert found == {"same": "identical", "changed": "conflict", "fresh": "new"}


def test_loose_skill_file_is_named_from_its_frontmatter(tmp_path, files_root):
    loose = tmp_path / "downloads" / "SKILL.md"
    loose.parent.mkdir()
    loose.write_text(SKILL.format(name="reviewer"))
    [candidate] = skills.discover(loose)
    skills.install(candidate)
    assert (files_root / "skills" / "reviewer" / "SKILL.md").read_text() == loose.read_text()


def test_files_list_skill_md_first_then_files_then_folders_with_their_contents(tmp_path):
    folder = tmp_path / "reviewer"
    write_skill(folder, "reviewer")
    (folder / "references").mkdir()
    (folder / "references" / "guide.md").write_text("guide")
    (folder / "LICENSE").write_text("license")
    skill = skills.Skill("reviewer", "", folder)
    assert [str(path) for path in skills.files(skill)] == ["SKILL.md", "LICENSE", "references", "references/guide.md"]
