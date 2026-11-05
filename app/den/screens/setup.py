from pathlib import Path
from typing import ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Center, Middle
from textual.widgets import Button, Static

from den.machine.settings import Settings
from den.services.folder_picker import FolderPickerUnavailable, pick_folder

__all__ = ["FilesSetup"]

PICKER_PROMPT = "Select your config folder"
SETUP_CSS = """
#setup-message, #setup-error { width: auto; margin: 1 0; }
#setup-error { color: $error; }
"""


class FilesSetup(App[Path]):
    CSS = SETUP_CSS
    BINDINGS: ClassVar[list[BindingType]] = [Binding("q", "quit", "Quit")]

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                yield Static("den needs the git repository holding your configs.", id="setup-message")
            with Center():
                yield Button(PICKER_PROMPT, id="select-folder", variant="primary")
            with Center():
                yield Static("", id="setup-error")

    @on(Button.Pressed, "#select-folder")
    def select_folder(self) -> None:
        self.choose_folder()

    @work(thread=True, exclusive=True)
    def choose_folder(self) -> None:
        try:
            folder = pick_folder(PICKER_PROMPT)
        except FolderPickerUnavailable as error:
            self.call_from_thread(self.show_error, str(error))
            return
        self.call_from_thread(self.use_folder, folder)

    def use_folder(self, folder: Path | None) -> None:
        if folder is None:
            return
        if not (folder / ".git").exists():
            self.show_error(f"Not a git repository: {folder}")
            return
        self.settings.files = folder
        self.settings.save()
        self.exit(folder)

    def show_error(self, message: str) -> None:
        self.query_one("#setup-error", Static).update(message)
