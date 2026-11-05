import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from den import agent_settings, backups
from den.machine.paths import instructions_file, skills_dir
from den.manifest.models import Agent

VERSION_TIMEOUT_SECONDS = 5
VERSION_UNKNOWN = "unknown"
LINKED = "linked"
ABSENT = "absent"
NO_GLOBAL_FILE = "no global file"
NOT_MANAGED = "not managed"
NEEDS_LINK = {"missing", "stale", "own folder", "own file"}
SETTINGS_APPLIED = "applied"
SETTINGS_PENDING = "pending"
NO_SETTINGS = "no settings"


@dataclass(frozen=True)
class AgentStatus:
    agent: Agent
    skills: str
    instructions: str
    settings: str
    version: str
    own_skills: tuple[str, ...]

    @property
    def needs_setup(self) -> bool:
        return self.skills in NEEDS_LINK or self.instructions in NEEDS_LINK or self.settings == SETTINGS_PENDING


def _version(agent: Agent) -> str:
    if not agent.version:
        return ""
    try:
        result = subprocess.run(
            ["bash", "-c", agent.version], capture_output=True, text=True, timeout=VERSION_TIMEOUT_SECONDS, check=False
        )
    except subprocess.TimeoutExpired:
        return VERSION_UNKNOWN
    lines = (result.stdout or result.stderr).strip().splitlines()
    return lines[0] if result.returncode == 0 and lines else VERSION_UNKNOWN


def _link_state(path: Path, source: Path) -> str:
    if path.is_symlink():
        return LINKED if path.resolve() == source.resolve() else "stale"
    if path.is_dir():
        return "own folder"
    return "own file" if path.exists() else "missing"


def _own_skills(skills: Path | None) -> tuple[str, ...]:
    if skills is None or skills.is_symlink() or not skills.is_dir():
        return ()
    names = (path.name for path in skills.iterdir() if path.is_dir() and not path.name.startswith("."))
    return tuple(sorted(name for name in names if not (skills_dir() / name).exists()))


def _settings_state(agent: Agent) -> str:
    if not agent.settings:
        return NO_SETTINGS
    applied = all(agent_settings.is_applied(settings) for settings in agent.settings)
    return SETTINGS_APPLIED if applied else SETTINGS_PENDING


def status(agent: Agent) -> AgentStatus:
    if not agent.home_path.exists():
        return AgentStatus(agent, ABSENT, ABSENT, ABSENT, "", ())
    skills, instructions = agent.skills_path, agent.instructions_path
    return AgentStatus(
        agent,
        _link_state(skills, skills_dir()) if skills else NOT_MANAGED,
        _link_state(instructions, instructions_file()) if instructions else NO_GLOBAL_FILE,
        _settings_state(agent),
        _version(agent),
        _own_skills(skills),
    )


def _replace_with_link(path: Path, source: Path, backup_name: str) -> None:
    if _link_state(path, source) == LINKED:
        return
    if path.is_symlink():
        path.unlink()
    elif path.exists():
        destination = backups.new_folder() / "agents" / backup_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(path, destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(source)


def set_up(agent: Agent) -> None:
    if agent.skills_path:
        _replace_with_link(agent.skills_path, skills_dir(), f"{agent.name}-skills")
    if agent.instructions_path:
        _replace_with_link(
            agent.instructions_path,
            instructions_file(),
            f"{agent.name}-{agent.instructions_path.name}",
        )
    for settings in agent.settings:
        if not agent_settings.is_applied(settings):
            agent_settings.apply(settings)
