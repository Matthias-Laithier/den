import os
import subprocess
from pathlib import Path

from textual.containers import Container
from textual.widgets import DataTable

from den.context import Context
from den.services.shell import run_steps

DEFAULT_EDITOR = "nvim"


class Pane(Container):
    def __init__(self, context: Context, **kwargs) -> None:
        super().__init__(**kwargs)
        self.context = context
        self.shown: object = None

    def reload(self) -> None:
        raise NotImplementedError

    def on_mount(self) -> None:
        self.loading = True

    def is_already_shown(self, data: object) -> bool:
        self.loading = False
        if data == self.shown:
            return True
        self.shown = data
        return False

    def report_error(self, error: Exception, title: str) -> None:
        self.app.call_from_thread(self.app.notify, str(error), title=title, severity="error")

    def run_in_terminal(self, steps: list[str]) -> list[str]:
        with self.app.suspend():
            return run_steps(steps)

    def edit(self, path: Path) -> None:
        with self.app.suspend():
            subprocess.run([os.environ.get("EDITOR", DEFAULT_EDITOR), str(path)], check=False)
        self.reload()

    def focus_content(self) -> None:
        focusable = self.query("DataTable, ListView")
        if focusable:
            focusable.first().focus()

    def highlighted_key(self, selector: str) -> str | None:
        table = self.query_one(selector, DataTable)
        if table.row_count == 0:
            return None
        return table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
