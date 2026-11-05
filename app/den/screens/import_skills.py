import tempfile
from pathlib import Path
from typing import ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, SelectionList, Static
from textual.widgets.selection_list import Selection

from den import skills
from den.screens.dialogs import diff_view
from den.services.remote_repositories import CloneFailed, shallow_clone

STATUS_STYLES = {"new": "green", "identical": "dim", "conflict": "bold red"}


class ImportSkillsScreen(ModalScreen[int]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss(0)", "Cancel"),
        Binding("i", "import_selected", "Import selected"),
    ]

    def __init__(self, source: str) -> None:
        super().__init__()
        self.source = source
        self.workspace: tempfile.TemporaryDirectory | None = None
        self.candidates: dict[str, skills.Candidate] = {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog wide"):
            yield Label(f"Import skills from {self.source}", classes="dialog-title")
            yield Label(
                "space select · i import · esc cancel · conflicts overwrite the skill in den", classes="dialog-hint"
            )
            with Horizontal(classes="split"):
                yield SelectionList[str](classes="list")
                with VerticalScroll(classes="detail"):
                    yield Static("Looking for skills…", id="candidate-detail")

    def on_mount(self) -> None:
        self.discover()

    def on_unmount(self) -> None:
        if self.workspace is not None:
            self.workspace.cleanup()

    @work(thread=True, exit_on_error=False)
    def discover(self) -> None:
        path = Path(self.source).expanduser()
        try:
            if not path.exists():
                self.workspace, path = shallow_clone(self.source)
            candidates = skills.discover(path)
        except CloneFailed as error:
            self.app.call_from_thread(self.query_one("#candidate-detail", Static).update, str(error))
            return
        self.app.call_from_thread(self.show, candidates)

    def show(self, candidates: list[skills.Candidate]) -> None:
        self.candidates = {candidate.name: candidate for candidate in candidates}
        selection_list = self.query_one(SelectionList)
        for candidate in candidates:
            label = f"[{STATUS_STYLES[candidate.status]}]{candidate.status:<9}[/] {candidate.name}"
            selection_list.add_option(Selection(label, candidate.name, candidate.status == "new"))
        selection_list.focus()
        self.query_one("#candidate-detail", Static).update(f"{len(candidates)} skills found")

    @on(SelectionList.SelectionHighlighted)
    def show_candidate(self, event: SelectionList.SelectionHighlighted) -> None:
        candidate = self.candidates[event.selection.value]
        detail = diff_view(skills.diff(candidate)) if candidate.status == "conflict" else candidate.description
        self.query_one("#candidate-detail", Static).update(detail)

    def action_import_selected(self) -> None:
        chosen = [self.candidates[name] for name in self.query_one(SelectionList).selected]
        for candidate in chosen:
            skills.install(candidate)
        self.dismiss(len(chosen))
