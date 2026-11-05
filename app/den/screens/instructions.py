from typing import ClassVar

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Static

from den import agents
from den.machine.paths import files_root, instructions_file
from den.screens.document_view import DocumentView
from den.screens.pane import Pane


def _header(linked: list[str], diff: str) -> Text:
    status = ("  ● modified", "yellow") if diff else ("  ✓ committed", "green")
    readers = ", ".join(linked) if linked else "no agent yet, set them up in the Agents tab"
    return Text.assemble(
        (str(instructions_file().relative_to(files_root())), "bold"),
        status,
        ("\nRead by ", "dim"),
        (readers, "italic dim"),
    )


class InstructionsPane(Pane):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("e", "edit_instructions", "Edit"),
        Binding("d", "toggle_diff", "Diff / preview"),
    ]

    def __init__(self, context, **kwargs) -> None:
        super().__init__(context, **kwargs)
        self.showing_diff = False
        self.diff = ""

    def compose(self) -> ComposeResult:
        yield Static(id="instructions-header")
        yield DocumentView(id="instructions-document")

    def on_mount(self) -> None:
        self.reload()

    @work(thread=True, exit_on_error=False, exclusive=True)
    def reload(self) -> None:
        statuses = [agents.status(agent) for agent in self.context.manifest().agents]
        linked = [status.agent.name for status in statuses if status.instructions == agents.LINKED]
        diff = self.context.repo.diff_path(instructions_file())
        self.app.call_from_thread(self.show, linked, diff)

    def show(self, linked: list[str], diff: str) -> None:
        if self.is_already_shown((linked, diff)):
            return
        self.diff = diff
        self.query_one("#instructions-header", Static).update(_header(linked, diff))
        self.render_document()

    def render_document(self) -> None:
        document = self.query_one(DocumentView)
        if self.showing_diff:
            document.show_diff(self.diff)
        else:
            document.show_file(instructions_file())

    def focus_content(self) -> None:
        self.query_one(DocumentView).focus()

    def action_toggle_diff(self) -> None:
        self.showing_diff = not self.showing_diff
        self.render_document()

    def action_edit_instructions(self) -> None:
        self.edit(instructions_file())
