from dataclasses import dataclass

from den.machine.settings import Settings
from den.machine.system import System
from den.manifest.loader import load
from den.manifest.models import Manifest
from den.services.git import Repo


@dataclass
class Context:
    system: System
    settings: Settings
    repo: Repo
    tool_repo: Repo

    def manifest(self) -> Manifest:
        return load(self.system, self.settings.profiles)
