from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, SelectionList
from textual.widgets.selection_list import Selection

from den.mcp import catalog
from den.mcp.models import McpServer


def _label(agent: str, server: McpServer, known: dict[str, McpServer]) -> str:
    if server.name in known and known[server.name].identity != server.identity:
        return f"[bold red]replaces[/] {server.name}  {server.target}  [dim]from {agent}[/]"
    return f"[green]new[/] {server.name}  {server.target}  [dim]from {agent}[/]"


class ImportMcpScreen(ModalScreen[bool]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss(False)", "Cancel"),
        Binding("i", "import_selected", "Import selected"),
    ]

    def __init__(self, extras: list[tuple[str, McpServer]], servers: list[McpServer]) -> None:
        super().__init__()
        self.extras = extras
        self.known = {server.name: server for server in servers}
        self.identities = {server.identity for server in servers}

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog wide"):
            yield Label("Servers only some agents have", classes="dialog-title")
            yield Label("space select · i import into manifest/mcp.toml · esc cancel", classes="dialog-hint")
            yield SelectionList[int](
                *(
                    Selection(_label(agent, server, self.known), index, server.identity not in self.identities)
                    for index, (agent, server) in enumerate(self.extras)
                )
            )

    def action_import_selected(self) -> None:
        chosen = [self.extras[index][1] for index in self.query_one(SelectionList).selected]
        catalog.import_servers(chosen)
        self.dismiss(bool(chosen))
