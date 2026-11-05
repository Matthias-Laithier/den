import shutil
from datetime import datetime
from pathlib import Path

from den.machine.paths import state_dir

FOLDER_FORMAT = "%Y%m%d-%H%M%S"


def root() -> Path:
    return state_dir() / "backups"


def new_folder() -> Path:
    return root() / datetime.now().astimezone().strftime(FOLDER_FORMAT)


def summary() -> tuple[int, int]:
    if not root().exists():
        return 0, 0
    folders = [path for path in root().iterdir() if path.is_dir()]
    size = sum(file.stat().st_size for file in root().rglob("*") if file.is_file() and not file.is_symlink())
    return len(folders), size


def clean() -> None:
    if root().exists():
        shutil.rmtree(root())
