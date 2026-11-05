from typing import ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import DataTable, Static

from den import links
from den.links import Link
from den.screens.dialogs import ConfirmScreen, diff_view
from den.screens.pane import Pane

STATE_STYLES = {"linked": "green", "missing": "yellow", "stale": "yellow", "conflict": "bold red"}


class ConfigsPane(Pane):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("l", "link", "Link"),
        Binding("L", "link_all", "Link all"),
        Binding("A", "adopt", "Adopt existing file"),
        Binding("e", "edit_config", "Edit"),
    ]

    def __init__(self, context, **kwargs) -> None:
        super().__init__(context, **kwargs)
        self.links: dict[str, Link] = {}

    def compose(self) -> ComposeResult:
        yield Static(
            "l link (a replaced file is backed up), L link all, A adopt the file already on disk into the repo",
            classes="pane-title",
        )
        with Horizontal(classes="split"):
            yield DataTable(id="links-table", cursor_type="row", classes="list")
            with VerticalScroll(classes="detail"):
                yield Static(id="config-diff")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns("State", "Package", "Path in home")

    @work(thread=True, exit_on_error=False, exclusive=True)
    def reload(self) -> None:
        planned = links.plan_all(self.context.manifest().link_packages)
        self.app.call_from_thread(self.show, planned)

    def show(self, planned: list[Link]) -> None:
        if self.is_already_shown(planned):
            return
        self.links = {link.relative: link for link in planned}
        table = self.query_one(DataTable)
        cursor = table.cursor_row
        table.clear()
        for link in planned:
            table.add_row(
                f"[{STATE_STYLES[link.state]}]{link.state}[/]", link.package, link.relative, key=link.relative
            )
        table.move_cursor(row=cursor)

    def highlighted_link(self) -> Link | None:
        return self.links.get(self.highlighted_key("#links-table") or "")

    @on(DataTable.RowHighlighted)
    def show_diff(self) -> None:
        link = self.highlighted_link()
        if link is not None:
            self.load_diff(link)

    @work(thread=True, exit_on_error=False, exclusive=True, group="diff")
    def load_diff(self, link: Link) -> None:
        diff = self.context.repo.diff_path(link.source) or f"{link.source}\n\nNo uncommitted changes"
        self.app.call_from_thread(self.query_one("#config-diff", Static).update, diff_view(diff))

    def action_link(self) -> None:
        link = self.highlighted_link()
        if link is None:
            return
        links.apply(link)
        self.reload()

    @work
    async def action_link_all(self) -> None:
        pending = [link for link in self.links.values() if link.state != "linked"]
        conflicts = sum(1 for link in pending if link.state == "conflict")
        question = f"Link {len(pending)} configs? {conflicts} existing files will be moved to a backup."
        if pending and await self.app.push_screen_wait(ConfirmScreen(question)):
            backup = links.apply_all(pending)
            self.app.notify(f"Backup in {backup}" if backup else "Linked")
        self.reload()

    @work
    async def action_adopt(self) -> None:
        link = self.highlighted_link()
        if link is None or link.state != "conflict":
            return
        question = f"Replace the repo version of {link.relative} with the file on disk?"
        if await self.app.push_screen_wait(ConfirmScreen(question)):
            links.adopt(link)
        self.reload()

    def action_edit_config(self) -> None:
        link = self.highlighted_link()
        if link is not None:
            self.edit(link.source)
