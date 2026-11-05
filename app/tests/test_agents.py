from den import agents
from den.manifest.models import Agent


def test_linking_points_skills_and_instructions_at_den_and_backs_up_the_originals(files_root, fake_home):
    den_skills = files_root / "skills"
    (den_skills / "shared").mkdir(parents=True)
    den_instructions = files_root / "instructions" / "AGENTS.md"
    den_instructions.parent.mkdir()
    den_instructions.write_text("shared rules")
    (fake_home / ".claude" / "skills" / "private").mkdir(parents=True)
    (fake_home / ".claude" / "CLAUDE.md").write_text("old rules")
    agent = Agent("claude", "~/.claude", "~/.claude/skills", None, None, "~/.claude/CLAUDE.md")
    before = agents.status(agent)
    assert (before.skills, before.instructions, before.own_skills) == ("own folder", "own file", ("private",))
    agents.set_up(agent)
    after = agents.status(agent)
    assert (after.skills, after.instructions) == ("linked", "linked")
    assert (fake_home / ".claude" / "CLAUDE.md").read_text() == "shared rules"
    backups = fake_home / ".local" / "share" / "den" / "backups"
    assert [path.read_text() for path in backups.glob("*/agents/claude-CLAUDE.md")] == ["old rules"]
    assert list(backups.glob("*/agents/claude-skills/private"))


def test_an_agent_without_a_skills_path_keeps_its_own_skills_folder(fake_home):
    (fake_home / ".hermes" / "skills" / "bundled").mkdir(parents=True)
    agent = Agent("hermes", "~/.hermes", None, None, None)
    agents.set_up(agent)
    status = agents.status(agent)
    assert (status.skills, status.own_skills, status.needs_setup) == ("not managed", (), False)
    assert (fake_home / ".hermes" / "skills" / "bundled").is_dir()
