import asyncio

from textual.app import App, ComposeResult
from textual.widgets import Markdown

from den.context import Context
from den.machine.paths import instructions_file
from den.machine.settings import Settings
from den.machine.system import detect
from den.screens.instructions import InstructionsPane
from den.services.git import Repo

NEW_RULE = "Commits use the conventional format `type(scope): summary`."


class InstructionsApp(App):
    def __init__(self, context: Context) -> None:
        super().__init__()
        self.context = context

    def compose(self) -> ComposeResult:
        yield InstructionsPane(self.context)


def test_a_committed_change_to_the_instructions_shows_after_a_reload(files_root, git):
    instructions_file().parent.mkdir()
    instructions_file().write_text("Commits are one-liners.\n")
    git(files_root, "init", "-q")
    git(files_root, "add", "--all")
    git(files_root, "commit", "-q", "-m", "initial")
    app = InstructionsApp(Context(detect(), Settings(), Repo(files_root), Repo(files_root)))

    async def reload_after_commit() -> str:
        async with app.run_test() as pilot:
            pane = app.query_one(InstructionsPane)
            pane.reload()
            await app.workers.wait_for_complete()
            instructions_file().write_text(f"{NEW_RULE}\n")
            git(files_root, "commit", "-q", "-a", "-m", "conventional commits")
            pane.reload()
            await app.workers.wait_for_complete()
            await pilot.pause()
            return app.query_one(Markdown).source

    assert asyncio.run(reload_after_commit()).strip() == NEW_RULE
