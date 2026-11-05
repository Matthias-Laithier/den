from typing import ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import DataTable, Static

from den import apply, packages, tasks
from den.manifest.models import Manifest
from den.screens import install_rows
from den.screens.dialogs import MessageScreen
from den.screens.pane import Pane

SELECTED_MARK = "●"


class InstallPane(Pane):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("space", "toggle_selection", "Select"),
        Binding("a", "select_missing", "Select missing"),
        Binding("i", "install", "Install"),
        Binding("u", "check_updates", "Check updates"),
        Binding("U", "update_all", "Update all"),
        Binding("t", "run_task", "Run task"),
        Binding("T", "run_pending_tasks", "Run pending tasks"),
    ]

    def __init__(self, context, **kwargs) -> None:
        super().__init__(context, **kwargs)
        self.manifest = Manifest()
        self.installed: dict[str, bool] = {}
        self.updates: dict[str, dict[str, str]] | None = None
        self.task_states: dict[str, str] = {}
        self.selected: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Static(id="install-summary", classes="summary")
        yield Static("Packages · space select · a select missing · i install · u check updates · U update all")
        yield DataTable(id="packages-table", cursor_type="row")
        yield Static("Setup tasks · t run the highlighted one · T run every pending one")
        yield DataTable(id="tasks-table", cursor_type="row")

    def on_mount(self) -> None:
        packages_table = self.query_one("#packages-table", DataTable)
        packages_table.add_columns("", "State", "Package", "Group", "With", "Update")
        self.query_one("#tasks-table", DataTable).add_columns("State", "Task", "Description")
        self.reload()
        self.action_check_updates()

    @work(thread=True, exit_on_error=False, exclusive=True)
    def reload(self) -> None:
        manifest = self.context.manifest()
        installed = packages.statuses(manifest.packages)
        task_states = {task.name: tasks.state(task) for task in manifest.tasks}
        self.app.call_from_thread(self.show, manifest, installed, task_states)

    def show(self, manifest: Manifest, installed: dict[str, bool], task_states: dict[str, str]) -> None:
        if self.is_already_shown((manifest, installed, task_states)):
            return
        self.manifest, self.installed, self.task_states = manifest, installed, task_states
        self.selected &= {name for name, done in installed.items() if not done}
        self.show_packages()
        table = self.query_one("#tasks-table", DataTable)
        table.clear()
        for task in sorted(manifest.tasks, key=lambda task: install_rows.task_rank(task_states[task.name])):
            table.add_row(install_rows.task_state(task_states[task.name]), task.name, task.description, key=task.name)

    def show_packages(self) -> None:
        updates = self.updates or {}
        table = self.query_one("#packages-table", DataTable)
        cursor = table.cursor_row
        table.clear()
        for package in sorted(
            self.manifest.packages, key=lambda p: install_rows.package_rank(p, self.installed, updates)
        ):
            table.add_row(
                SELECTED_MARK if package.name in self.selected else "",
                install_rows.package_state(package.name, self.installed, updates),
                package.name,
                package.group,
                package.method,
                install_rows.update_label(package.name, updates),
                key=package.name,
            )
        table.move_cursor(row=cursor)
        missing = sum(1 for done in self.installed.values() if not done)
        outdated = None if self.updates is None else len(self.updates)
        pending = sum(1 for state in self.task_states.values() if state == "pending")
        self.query_one("#install-summary", Static).update(install_rows.summary(missing, outdated, pending))

    def action_toggle_selection(self) -> None:
        name = self.highlighted_key("#packages-table")
        if name is None or self.installed.get(name):
            return
        self.selected ^= {name}
        self.show_packages()

    def action_select_missing(self) -> None:
        self.selected = {name for name, done in self.installed.items() if not done}
        self.show_packages()

    def action_install(self) -> None:
        chosen = self.selected or {self.highlighted_key("#packages-table")}
        to_install = [package for package in self.manifest.packages if package.name in chosen]
        if to_install:
            self.finish("Installed", self.run_in_terminal(packages.install_steps(to_install)))
            self.selected.clear()

    @work(thread=True, exit_on_error=False, exclusive=True, group="updates")
    def action_check_updates(self) -> None:
        manifest = self.context.manifest()
        installed = packages.statuses(manifest.packages)
        found = packages.updates([package for package in manifest.packages if installed[package.name]])
        self.app.call_from_thread(self.set_updates, found)

    def set_updates(self, found: dict[str, dict[str, str]]) -> None:
        self.updates = found
        self.show_packages()

    def action_update_all(self) -> None:
        if not self.updates:
            self.app.notify("Nothing to update, press u to check", severity="warning")
            return
        steps = packages.update_steps(self.manifest.packages, self.updates)
        self.finish("Updated", self.run_in_terminal(steps))
        self.updates = None

    def finish(self, success: str, failed: list[str]) -> None:
        self.app.notify(
            f"{len(failed)} steps failed" if failed else success, severity="warning" if failed else "information"
        )
        self.reload()

    @on(DataTable.RowSelected, "#tasks-table")
    def action_run_task(self) -> None:
        name = self.highlighted_key("#tasks-table")
        task = next((task for task in self.manifest.tasks if task.name == name), None)
        if task is None:
            return
        if task.manual:
            self.app.push_screen(MessageScreen(task.description, task.manual))
            return
        if task.run:
            self.run_in_terminal([task.run])
        self.reload()

    def action_run_pending_tasks(self) -> None:
        pending = [task.run for task in apply.pending_tasks(self.manifest) if task.run]
        if not pending:
            self.app.notify("No pending tasks")
            return
        self.finish(f"Ran {len(pending)} tasks", self.run_in_terminal(pending))
