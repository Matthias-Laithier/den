from dataclasses import dataclass, field
from pathlib import Path

from den.machine.paths import expand


@dataclass(frozen=True)
class Package:
    name: str
    group: str
    method: str
    targets: tuple[str, ...]
    check: str | None
    post_install: str | None


@dataclass(frozen=True)
class Task:
    name: str
    description: str
    check: str | None
    run: str | None
    manual: str | None


@dataclass(frozen=True)
class SettingsFile:
    file: str
    values: dict

    @property
    def path(self) -> Path:
        return expand(self.file)


@dataclass(frozen=True)
class Agent:
    name: str
    home: str
    skills: str | None
    package: str | None
    version: str | None
    instructions: str | None = None
    settings: tuple[SettingsFile, ...] = ()

    @property
    def home_path(self) -> Path:
        return expand(self.home)

    @property
    def skills_path(self) -> Path | None:
        return expand(self.skills) if self.skills else None

    @property
    def instructions_path(self) -> Path | None:
        return expand(self.instructions) if self.instructions else None


@dataclass
class Manifest:
    packages: list[Package] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    agents: list[Agent] = field(default_factory=list)
    link_packages: list[str] = field(default_factory=list)
