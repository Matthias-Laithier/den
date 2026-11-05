from typing import ClassVar

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Input, Label, ListItem, ListView, Static

from den.screens.dialogs import diff_view
from den.screens.pane import Pane
from den.services.git import Change, GitError, RepoState

STATUS_STYLES = {
    "new": "green",
    "added": "green",
    "modified": "yellow",
    "deleted": "red",
    "renamed": "cyan",
    "copied": "cyan",
    "conflict": "bold red",
}


class ChangeItem(ListItem):
    def __init__(self, change: Change) -> None:
        super().__init__()
        self.change = change

    def compose(self) -> ComposeResult:
        label = self.change.label
        yield Label(Text.assemble((f"{label:<9}", STATUS_STYLES.get(label, "")), self.change.path))


class ChangesPane(Pane):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("c", "focus_commit", "Commit & push"),
        Binding("p", "pull", "Pull"),
        Binding("P", "push", "Push"),
        Binding("e", "edit_change", "Edit"),
    ]

    def __init__(self, context, **kwargs) -> None:
        super().__init__(context, **kwargs)
        self.changes: list[Change] = []

    def compose(self) -> ComposeResult:
        with Horizontal(classes="split"):
            yield ListView(id="change-list", classes="list")
            with VerticalScroll(classes="detail"):
                yield Static(id="change-diff")
        yield Input(placeholder="Commit message, enter commits every change and pushes", id="commit-message")

    @work(thread=True, exit_on_error=False, exclusive=True, group="state")
    def reload(self) -> None:
        state = self.context.repo.state()
        self.app.call_from_thread(self.show, state)

    async def show(self, state: RepoState) -> None:
        self.loading = False
        if state.changes == self.changes:
            return
        self.changes = state.changes
        change_list = self.query_one(ListView)
        selected = self.selected_change()
        await change_list.clear()
        await change_list.extend(ChangeItem(change) for change in state.changes)
        paths = [change.path for change in state.changes]
        change_list.index = paths.index(selected.path) if selected and selected.path in paths else 0
        if not paths:
            self.query_one("#change-diff", Static).update("Nothing to commit")

    def selected_change(self) -> Change | None:
        item = self.query_one(ListView).highlighted_child
        return item.change if isinstance(item, ChangeItem) else None

    @on(ListView.Highlighted)
    def show_selected_diff(self) -> None:
        if change := self.selected_change():
            self.load_diff(change)

    @work(thread=True, exit_on_error=False, exclusive=True, group="diff")
    def load_diff(self, change: Change) -> None:
        try:
            diff = self.context.repo.diff(change)
        except GitError as error:
            diff = str(error)
        self.app.call_from_thread(self.query_one("#change-diff", Static).update, diff_view(diff))

    def action_focus_commit(self) -> None:
        self.query_one("#commit-message", Input).focus()

    @on(Input.Submitted, "#commit-message")
    def submit_commit(self, event: Input.Submitted) -> None:
        message = event.value.strip()
        if not message:
            self.app.notify("Write a commit message first", severity="warning")
            return
        event.input.clear()
        self.query_one(ListView).focus()
        self.run_git(lambda: self.commit_and_push(message), "Committed and pushed")

    def commit_and_push(self, message: str) -> None:
        self.context.repo.commit(message)
        self.context.repo.push()

    def action_pull(self) -> None:
        self.run_git(self.context.repo.pull, "Pulled")

    def action_push(self) -> None:
        self.run_git(self.context.repo.push, "Pushed")

    @work(thread=True, exit_on_error=False, exclusive=True, group="git")
    def run_git(self, operation, success: str) -> None:
        try:
            operation()
        except GitError as error:
            self.report_error(error, "git")
        else:
            self.app.call_from_thread(self.app.notify, success)
        self.app.call_from_thread(self.reload)

    def action_edit_change(self) -> None:
        change = self.selected_change()
        if change is not None and change.label != "deleted":
            self.edit(self.context.repo.root / change.path)
