from pathlib import Path
from typing import ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Center, Vertical
from textual.widgets import Button, Footer, Static

from den.machine.settings import Settings
from den.services.folder_picker import FolderPickerUnavailable, pick_folder
from den.theme import STYLESHEET, THEME

__all__ = ["FilesSetup"]

PICKER_PROMPT = "Select your config folder"


class FilesSetup(App[Path]):
    TITLE = "den"
    CSS_PATH = STYLESHEET
    BINDINGS: ClassVar[list[BindingType]] = [Binding("q", "quit", "Quit")]

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        with Center(id="setup-screen"), Vertical(id="setup"):
            yield Static("Welcome to den", classes="dialog-title")
            yield Static(
                "Pick the git repository holding your configs. den remembers it.",
                classes="dialog-hint",
            )
            with Center(id="setup-actions"):
                yield Button(PICKER_PROMPT, id="select-folder", variant="primary", compact=True)
            yield Static("", id="setup-error")
        yield Footer()

    def on_mount(self) -> None:
        self.theme = THEME
        self.query_one("#select-folder", Button).focus()

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
        error = self.query_one("#setup-error", Static)
        error.update(message)
        error.add_class("shown")
