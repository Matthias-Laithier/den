from typing import ClassVar

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static

DIFF_THEME = "ansi_dark"


def diff_view(diff: str) -> Syntax:
    return Syntax(diff, "diff", theme=DIFF_THEME)


class PromptScreen(ModalScreen[str | None]):
    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "dismiss(None)", "Cancel")]

    def __init__(self, title: str, placeholder: str = "", password: bool = False, value: str = "") -> None:
        super().__init__()
        self.prompt_title = title
        self.input = Input(value=value, placeholder=placeholder, password=password)

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self.prompt_title, classes="dialog-title")
            yield self.input

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("y", "dismiss(True)", "Yes"),
        Binding("n,escape", "dismiss(False)", "No"),
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self.question, classes="dialog-title")
            yield Label("y: yes   n: no", classes="dialog-hint")


class MessageScreen(ModalScreen[None]):
    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape,enter,q", "dismiss(None)", "Close")]

    def __init__(self, title: str, body) -> None:
        super().__init__()
        self.message_title = title
        self.body = body

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog wide"):
            yield Label(self.message_title, classes="dialog-title")
            with VerticalScroll():
                yield Static(self.body)
