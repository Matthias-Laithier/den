import os
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer, Static, TabbedContent, TabPane
from textual.worker import Worker, WorkerState

from den import apply, links
from den.context import Context
from den.machine.paths import FILES_ENV, ROOT
from den.machine.settings import Settings
from den.machine.system import detect
from den.screens.agents import AgentsPane
from den.screens.changes import ChangesPane
from den.screens.configs import ConfigsPane
from den.screens.install import InstallPane
from den.screens.instructions import InstructionsPane
from den.screens.mcp import McpPane
from den.screens.overview import OverviewPane
from den.screens.pane import Pane
from den.screens.secrets import SecretsPane
from den.screens.setup import FilesSetup
from den.screens.skills import SkillsPane
from den.services.git import GitError, Repo, RepoState

STYLESHEET = Path(__file__).parents[1] / "assets" / "styles" / "den.tcss"
THEME = "tokyo-night"
STATE_REFRESH_SECONDS = 5
BACKGROUND_ERROR_SECONDS = 15
PANES = [
    ("Overview", OverviewPane),
    ("Install", InstallPane),
    ("Configs", ConfigsPane),
    ("Skills", SkillsPane),
    ("Instructions", InstructionsPane),
    ("Agents", AgentsPane),
    ("MCP", McpPane),
    ("Secrets", SecretsPane),
    ("Changes", ChangesPane),
]


class StatusBar(Static):
    def show(self, context: Context, state: RepoState) -> None:
        sync = f"↑{state.ahead} ↓{state.behind}" if state.upstream else "no upstream"
        changed = (f"● {len(state.changes)} changed", "yellow" if state.changes else "green")
        system = context.system
        self.update(
            Text.assemble(("den", "bold"), f"  {system.name} {system.arch}  ⎇ {state.branch}  {sync}  ", changed)
        )


class Den(App):
    TITLE = "den"
    CSS_PATH = STYLESHEET
    BINDINGS: ClassVar[list[BindingType]] = [Binding("r", "reload", "Refresh"), Binding("q", "quit", "Quit")]

    def __init__(self, context: Context) -> None:
        super().__init__()
        self.context = context

    def compose(self) -> ComposeResult:
        yield StatusBar()
        with TabbedContent():
            for title, pane_class in PANES:
                with TabPane(title, id=title.lower()):
                    yield pane_class(self.context)
        yield Footer()

    def on_mount(self) -> None:
        self.theme = THEME
        self.context.repo.ensure_hooks()
        self.pull_on_launch()
        self.set_interval(STATE_REFRESH_SECONDS, self.refresh_state)

    @work(thread=True, exit_on_error=False, exclusive=True, group="launch")
    def pull_on_launch(self) -> None:
        for name, repo in (("files", self.context.repo), ("den", self.context.tool_repo)):
            try:
                if repo.upstream() is not None:
                    repo.pull()
            except GitError as error:
                self.call_from_thread(self.notify, str(error), title=f"Pull failed: {name}", severity="error")
        relinked = [link for link in apply.pending_links(self.context.manifest()) if link.state == "missing"]
        for link in relinked:
            links.apply(link)
        if relinked:
            self.call_from_thread(self.notify, f"Linked {len(relinked)} configs")
        self.call_from_thread(self.refresh_state)

    @work(thread=True, exit_on_error=False, exclusive=True, group="state")
    def refresh_state(self) -> None:
        try:
            state = self.context.repo.state()
        except GitError as error:
            self.call_from_thread(self.notify, str(error), title="git", severity="error")
            return
        self.call_from_thread(self.query_one(StatusBar).show, self.context, state)
        self.call_from_thread(self.query_one(ChangesPane).show, state)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.ERROR:
            self.notify(
                str(event.worker.error), title="Something failed", severity="error", timeout=BACKGROUND_ERROR_SECONDS
            )

    @on(TabbedContent.TabActivated)
    def reload_active_pane(self, event: TabbedContent.TabActivated) -> None:
        pane = event.pane.query_one(Pane)
        pane.reload()
        pane.focus_content()

    def action_reload(self) -> None:
        active_pane = self.query_one(TabbedContent).active_pane
        if active_pane is not None:
            active_pane.query_one(Pane).reload()
        self.refresh_state()


def run() -> None:
    settings = Settings.load()
    files = settings.files
    if files is None or not (files / ".git").exists():
        files = FilesSetup(settings).run()
        if files is None:
            return
    os.environ[FILES_ENV] = str(files)
    os.environ["DEN_ROOT"] = str(files)
    Den(Context(detect(), settings, Repo(files), Repo(ROOT))).run()
