import asyncio

from den.machine.settings import Settings
from den.screens import setup
from den.screens.setup import FilesSetup


def test_selecting_a_git_folder_saves_it_and_closes_setup(fake_home, tmp_path, monkeypatch):
    files = tmp_path / "den-files"
    (files / ".git").mkdir(parents=True)
    monkeypatch.setattr(setup, "pick_folder", lambda prompt: files)
    app = FilesSetup(Settings())

    async def select_folder() -> None:
        async with app.run_test() as pilot:
            await pilot.click("#select-folder")
            await app.workers.wait_for_complete()
            await pilot.pause()

    asyncio.run(select_folder())

    assert app.return_value == files
    assert Settings.load().files == files
