from dataclasses import dataclass, field
from pathlib import Path

import tomlkit

from den.machine.files import write_atomically
from den.machine.paths import config_dir, expand

SETTINGS_FILE_NAME = "config.toml"


@dataclass
class Settings:
    profiles: list[str] = field(default_factory=list)
    files: Path | None = None

    @classmethod
    def load(cls) -> "Settings":
        path = config_dir() / SETTINGS_FILE_NAME
        if not path.exists():
            return cls()
        data = tomlkit.parse(path.read_text())
        files = data.get("files")
        return cls(
            profiles=[str(profile) for profile in data.get("profiles", [])],
            files=expand(str(files)) if files else None,
        )

    def save(self) -> None:
        document = tomlkit.document()
        document["profiles"] = self.profiles
        if self.files is not None:
            document["files"] = str(self.files)
        write_atomically(config_dir() / SETTINGS_FILE_NAME, tomlkit.dumps(document))

    def toggle_profile(self, profile: str) -> None:
        if profile in self.profiles:
            self.profiles.remove(profile)
        else:
            self.profiles.append(profile)
        self.save()
