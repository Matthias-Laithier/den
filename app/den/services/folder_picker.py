import platform
import subprocess
from pathlib import Path

from den.services.shell import is_available

__all__ = ["FolderPickerUnavailable", "pick_folder"]

DIALOG_TIMEOUT_SECONDS = 600
FOLDER_PICKER_UNAVAILABLE_MESSAGE = (
    'No folder picker available. Install zenity or kdialog, or set files = "<path>" in ~/.config/den/config.toml.'
)


class FolderPickerUnavailable(Exception):
    pass


def _selected_path(command: list[str]) -> Path | None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=DIALOG_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    selected = result.stdout.strip()
    return Path(selected) if result.returncode == 0 and selected else None


def _pick_macos(prompt: str) -> Path | None:
    script = f'POSIX path of (choose folder with prompt "{prompt}")'
    return _selected_path(["osascript", "-e", script])


def _linux_command(prompt: str) -> list[str]:
    if is_available("zenity"):
        return ["zenity", "--file-selection", "--directory", "--title", prompt]
    if is_available("kdialog"):
        return ["kdialog", "--getexistingdirectory", "--title", prompt]
    raise FolderPickerUnavailable(FOLDER_PICKER_UNAVAILABLE_MESSAGE)


def _pick_linux(prompt: str) -> Path | None:
    return _selected_path(_linux_command(prompt))


def pick_folder(prompt: str) -> Path | None:
    system = platform.system()
    if system == "Darwin":
        return _pick_macos(prompt)
    if system == "Linux":
        return _pick_linux(prompt)
    raise FolderPickerUnavailable(FOLDER_PICKER_UNAVAILABLE_MESSAGE)
