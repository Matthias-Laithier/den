from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import DataTable, Static

from den.machine.files import ChangedConcurrently
from den.mcp import catalog
from den.mcp.catalog import AgentServers
from den.mcp.models import McpServer
from den.screens.dialogs import ConfirmScreen
from den.screens.import_mcp import ImportMcpScreen
from den.screens.pane import Pane

STATE_MARKS = {"synced": "[green]✓[/]", "missing": "[yellow]missing[/]", "different": "[bold red]different[/]"}


class McpPane(Pane):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("s", "sync", "Sync to every agent"),
        Binding("i", "import_extras", "Import from agents"),
        Binding("x", "remove", "Remove"),
        Binding("e", "edit_servers", "Edit list"),
    ]

    def __init__(self, context, **kwargs) -> None:
        super().__init__(context, **kwargs)
        self.servers: list[McpServer] = []
        self.comparisons: list[AgentServers] = []

    def compose(self) -> ComposeResult:
        yield Static(
            "MCP servers from manifest/mcp.toml. Sync makes every agent's list match it, logins stay in each agent",
            classes="pane-title",
        )
        yield DataTable(id="mcp-table", cursor_type="row")
        yield Static(id="mcp-extras", classes="pane-title")

    @work(thread=True, exit_on_error=False, exclusive=True)
    def reload(self) -> None:
        servers = catalog.load_servers()
        agents = catalog.managed_agents(self.context.manifest().agents)
        comparisons = [catalog.compare(agent, servers) for agent in agents]
        self.app.call_from_thread(self.show, servers, comparisons)

    def show(self, servers: list[McpServer], comparisons: list[AgentServers]) -> None:
        if self.is_already_shown((servers, comparisons)):
            return
        self.servers, self.comparisons = servers, comparisons
        table = self.query_one(DataTable)
        cursor = table.cursor_row
        table.clear(columns=True)
        table.add_columns("Server", "Target", *(comparison.agent for comparison in comparisons))
        for server in servers:
            marks = (STATE_MARKS[comparison.states[server.name]] for comparison in comparisons)
            table.add_row(server.name, server.target, *marks, key=server.name)
        table.move_cursor(row=cursor)
        self.query_one("#mcp-extras", Static).update(self.extras_text())

    def extras_text(self) -> str:
        extras = [f"{c.agent}: {', '.join(s.name for s in c.extras)}" for c in self.comparisons if c.extras]
        if not extras:
            return "No agent has servers outside this list"
        return "Only in agents, removed by the next sync unless imported with i:  " + "   ".join(extras)

    @work
    async def action_sync(self) -> None:
        question = (
            f"Write these {len(self.servers)} servers to {len(self.comparisons)} agents? Their files are backed up."
        )
        if not await self.app.push_screen_wait(ConfirmScreen(question)):
            return
        self.sync_all()

    @work(thread=True, exit_on_error=False, exclusive=True, group="sync")
    def sync_all(self) -> None:
        try:
            for comparison in self.comparisons:
                catalog.sync(comparison.agent, self.servers)
        except ChangedConcurrently as error:
            self.report_error(error, "MCP sync")
        self.app.call_from_thread(self.reload)

    @work
    async def action_import_extras(self) -> None:
        extras = [(c.agent, server) for c in self.comparisons for server in c.extras]
        if extras and await self.app.push_screen_wait(ImportMcpScreen(extras, self.servers)):
            self.reload()

    @work
    async def action_remove(self) -> None:
        name = self.highlighted_key("#mcp-table")
        if name and await self.app.push_screen_wait(ConfirmScreen(f"Remove {name}? Agents lose it at the next sync.")):
            catalog.remove_server(name)
        self.reload()

    def action_edit_servers(self) -> None:
        self.edit(catalog.servers_file())
