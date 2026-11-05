import os
import re
from pathlib import Path

ROOT = Path(__file__).parents[3]
FILES_ENV = "DEN_FILES"
SHELL_DEFAULT = re.compile(r"\$\{(\w+):-([^}]*)\}")


def files_root() -> Path:
    return Path(os.environ[FILES_ENV])


def home_packages() -> Path:
    return files_root() / "home"


def skills_dir() -> Path:
    return files_root() / "skills"


def instructions_file() -> Path:
    return files_root() / "instructions" / "AGENTS.md"


def manifest_dir() -> Path:
    return files_root() / "manifest"


def secrets_dir() -> Path:
    return files_root() / "secrets"


def home() -> Path:
    return Path.home()


def config_dir() -> Path:
    return home() / ".config" / "den"


def state_dir() -> Path:
    return home() / ".local" / "share" / "den"


def expand(path: str) -> Path:
    with_defaults = SHELL_DEFAULT.sub(lambda match: os.environ.get(match.group(1)) or match.group(2), path)
    return Path(os.path.expanduser(os.path.expandvars(with_defaults)))
