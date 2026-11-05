import subprocess
from pathlib import Path

import pytest

from den.services import folder_picker
from den.services.folder_picker import FolderPickerUnavailable, pick_folder


def test_pick_folder_returns_the_selected_path_or_none_when_cancelled(monkeypatch):
    monkeypatch.setattr(folder_picker.platform, "system", lambda: "Darwin")
    commands = []

    def select(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=" /tmp/chosen \n", stderr="")

    monkeypatch.setattr(folder_picker.subprocess, "run", select)
    assert pick_folder("Pick the git repository holding your den files") == Path("/tmp/chosen")
    assert commands == [
        [
            "osascript",
            "-e",
            'POSIX path of (choose folder with prompt "Pick the git repository holding your den files")',
        ]
    ]

    monkeypatch.setattr(
        folder_picker.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, stdout="", stderr=""),
    )
    assert pick_folder("Pick") is None


def test_pick_folder_raises_when_linux_has_no_dialog(monkeypatch):
    monkeypatch.setattr(folder_picker.platform, "system", lambda: "Linux")
    monkeypatch.setattr(folder_picker, "is_available", lambda program: False)

    with pytest.raises(FolderPickerUnavailable):
        pick_folder("Pick")
