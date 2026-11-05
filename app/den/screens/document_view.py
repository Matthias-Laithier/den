from pathlib import Path

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Markdown, Static

from den import skills
from den.screens.dialogs import diff_view

MARKDOWN_SUFFIXES = {".md", ".markdown"}
CODE_THEME = "ansi_dark"
NO_CHANGES = "No uncommitted changes"


class DocumentView(VerticalScroll):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Markdown(classes="document-markdown")
        yield Static(classes="document-code")

    def _show_code(self, renderable) -> None:
        self.query_one(Markdown).display = False
        code = self.query_one(".document-code", Static)
        code.display = True
        code.update(renderable)

    def show_file(self, path: Path) -> None:
        self.path = path
        if path.suffix.lower() in MARKDOWN_SUFFIXES:
            self.query_one(".document-code", Static).display = False
            markdown = self.query_one(Markdown)
            markdown.display = True
            markdown.update(skills.markdown_body(path))
        else:
            self._show_code(Syntax(path.read_text(errors="replace"), Syntax.guess_lexer(str(path)), theme=CODE_THEME))
        self.scroll_home(animate=False)

    def show_diff(self, diff: str) -> None:
        self._show_code(diff_view(diff) if diff else NO_CHANGES)
        self.scroll_home(animate=False)
