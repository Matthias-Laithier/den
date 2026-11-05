from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import DataTable, Static

from den import agents, apply
from den.agents import AgentStatus
from den.machine.paths import instructions_file
from den.screens.dialogs import ConfirmScreen
from den.screens.import_skills import ImportSkillsScreen
from den.screens.pane import Pane

STATE_STYLES = {
    "linked": "green",
    "missing": "yellow",
    "stale": "yellow",
    "own folder": "yellow",
    "own file": "yellow",
    "absent": "dim",
    "no global file": "dim",
    "applied": "green",
    "pending": "bold yellow",
    "no settings": "dim",
}


def styled(state: str) -> str:
    return f"[{STATE_STYLES[state]}]{state}[/]"


class AgentsPane(Pane):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("l", "link", "Set up"),
        Binding("L", "link_all", "Set up all"),
        Binding("i", "import_own_skills", "Import its skills"),
        Binding("e", "edit_instructions", "Edit AGENTS.md"),
    ]

    def __init__(self, context, **kwargs) -> None:
        super().__init__(context, **kwargs)
        self.statuses: dict[str, AgentStatus] = {}

    def compose(self) -> ComposeResult:
        yield Static(
            "Set up links each agent's skills and instructions to den and applies its den settings",
            classes="pane-title",
        )
        yield DataTable(id="agents-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns(
            "Agent", "Skills", "Instructions", "Settings", "Version", "Skills not in den"
        )
        self.reload()

    @work(thread=True, exit_on_error=False, exclusive=True)
    def reload(self) -> None:
        statuses = [agents.status(agent) for agent in self.context.manifest().agents]
        self.app.call_from_thread(self.show, statuses)

    def show(self, statuses: list[AgentStatus]) -> None:
        if self.is_already_shown(statuses):
            return
        self.statuses = {status.agent.name: status for status in statuses}
        table = self.query_one(DataTable)
        cursor = table.cursor_row
        table.clear()
        for status in sorted(statuses, key=lambda status: status.skills == agents.ABSENT):
            table.add_row(
                status.agent.name,
                styled(status.skills),
                styled(status.instructions),
                styled(status.settings),
                status.version,
                ", ".join(status.own_skills),
                key=status.agent.name,
            )
        table.move_cursor(row=cursor)

    def highlighted_status(self) -> AgentStatus | None:
        return self.statuses.get(self.highlighted_key("#agents-table") or "")

    @work
    async def action_link(self) -> None:
        status = self.highlighted_status()
        if status is None or not status.needs_setup:
            return
        if status.own_skills:
            question = (
                f"{len(status.own_skills)} skills are not in den yet, link anyway? The folder is moved to a backup."
            )
            if not await self.app.push_screen_wait(ConfirmScreen(question)):
                return
        agents.set_up(status.agent)
        self.reload()

    def action_link_all(self) -> None:
        linkable = apply.linkable_agents(self.context.manifest())
        for status in linkable:
            agents.set_up(status.agent)
        self.app.notify(
            f"Set up {len(linkable)} agents, agents with skills not in den were skipped (import them with i)"
        )
        self.reload()

    @work
    async def action_import_own_skills(self) -> None:
        status = self.highlighted_status()
        if status is None or not status.own_skills:
            return
        imported = await self.app.push_screen_wait(ImportSkillsScreen(str(status.agent.skills_path)))
        self.app.notify(f"Imported {imported} skills")
        self.reload()

    def action_edit_instructions(self) -> None:
        self.edit(instructions_file())
