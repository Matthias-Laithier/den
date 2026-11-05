from dataclasses import dataclass
from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import DataTable, Static

from den import agents, apply, backups, links, packages, secrets, skills, tasks
from den.context import Context
from den.mcp import catalog
from den.screens.dialogs import ConfirmScreen
from den.screens.pane import Pane

WORK_PROFILE = "work"
BYTES_PER_MEGABYTE = 1024 * 1024


@dataclass(frozen=True)
class Summary:
    rows: list[tuple[str, str]]


def _count(states, wanted: str) -> int:
    return sum(1 for state in states if state == wanted)


def mcp_state(manifest_agents) -> str:
    servers = catalog.load_servers()
    comparisons = [catalog.compare(agent, servers) for agent in catalog.managed_agents(manifest_agents)]
    in_sync = sum(1 for c in comparisons if set(c.states.values()) <= {"synced"} and not c.extras)
    return f"{len(servers)} servers · {in_sync}/{len(comparisons)} agents in sync"


def backups_state() -> str:
    folders, size = backups.summary()
    return f"{folders} folders · {size / BYTES_PER_MEGABYTE:.1f} MB in {backups.root()}" if folders else "none"


def summarize(context: Context) -> Summary:
    manifest = context.manifest()
    installed = packages.statuses(manifest.packages).values()
    task_states = list(tasks.states(manifest.tasks).values())
    link_states = [link.state for link in links.plan_all(manifest.link_packages)]
    agent_states = [agents.status(agent).skills for agent in manifest.agents]
    secret_state = (
        "needs unlock" if secrets.is_outdated() else f"{len(secrets.local_names())}/{len(secrets.names())} set"
    )
    return Summary(
        [
            (
                "System",
                f"{context.system.name} · {context.system.arch} · profiles: {', '.join(context.settings.profiles) or 'none'}",
            ),
            ("Packages", f"{sum(installed)}/{len(manifest.packages)} installed"),
            ("Tasks", f"{_count(task_states, 'pending')} pending · {_count(task_states, 'manual')} manual"),
            ("Configs", f"{_count(link_states, 'linked')}/{len(link_states)} linked"),
            (
                "Agents",
                f"{_count(agent_states, 'linked')} linked · {len(agent_states) - _count(agent_states, 'absent')} installed",
            ),
            ("Skills", f"{len(skills.installed())} in den"),
            ("MCP", mcp_state(manifest.agents)),
            ("Secrets", secret_state),
            ("Backups", backups_state()),
        ]
    )


class OverviewPane(Pane):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+a", "apply_everything", "Apply everything"),
        Binding("w", "toggle_work", "Toggle work profile"),
        Binding("b", "clean_backups", "Clean backups"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Everything this machine should have, from the repo", classes="pane-title")
        yield DataTable(id="overview-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns("Area", "State")

    @work(thread=True, exit_on_error=False, exclusive=True)
    def reload(self) -> None:
        summary = summarize(self.context)
        self.app.call_from_thread(self.show, summary)

    def show(self, summary: Summary) -> None:
        if self.is_already_shown(summary):
            return
        table = self.query_one(DataTable)
        table.clear()
        for area, state in summary.rows:
            table.add_row(area, state)

    def action_toggle_work(self) -> None:
        self.context.settings.toggle_profile(WORK_PROFILE)
        self.reload()

    def action_apply_everything(self) -> None:
        manifest = self.context.manifest()
        with self.app.suspend():
            failed = apply.apply_everything(manifest)
        self.app.notify(
            f"{len(failed)} steps failed" if failed else "Machine is up to date",
            severity="warning" if failed else "information",
        )
        self.reload()

    @work
    async def action_clean_backups(self) -> None:
        folders, size = backups.summary()
        question = f"Delete {folders} backup folders ({size / BYTES_PER_MEGABYTE:.1f} MB)? They can't be restored."
        if folders and await self.app.push_screen_wait(ConfirmScreen(question)):
            backups.clean()
            self.app.notify("Backups deleted")
        self.reload()
