from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import DataTable, Static

from den import secrets
from den.screens.dialogs import ConfirmScreen, PromptScreen
from den.screens.pane import Pane


class SecretsPane(Pane):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("u", "unlock", "Unlock on this machine"),
        Binding("a", "set_secret", "Add or change"),
        Binding("x", "remove_secret", "Remove"),
        Binding("m", "migrate", "Encrypt from current shell"),
        Binding("p", "change_passphrase", "Change passphrase"),
    ]

    def __init__(self, context, **kwargs) -> None:
        super().__init__(context, **kwargs)
        self.passphrase: str | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="secrets-status", classes="pane-title")
        yield DataTable(id="secrets-table", cursor_type="row")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns("Secret", "On this machine")
        self.reload()

    def reload(self) -> None:
        local = secrets.local_names()
        status = self.status_text()
        if self.is_already_shown((secrets.names(), local, status)):
            return
        table = self.query_one(DataTable)
        table.clear()
        for name in secrets.names():
            table.add_row(name, "✓" if name in local else "✗", key=name)
        self.query_one("#secrets-status", Static).update(status)

    def status_text(self) -> str:
        if not secrets.has_vault():
            return "No secrets.age yet: m encrypts the listed secrets from your current shell"
        if secrets.is_outdated():
            return "secrets.age changed: u unlocks it into ~/.config/den/secrets.zsh"
        return f"Decrypted into {secrets.local_file()}, open a new shell to load changes"

    async def ask_passphrase(self) -> str | None:
        if self.passphrase is not None:
            return self.passphrase
        passphrase = await self.app.push_screen_wait(PromptScreen("Secrets passphrase", password=True))
        if not passphrase:
            return None
        try:
            secrets.decrypt(passphrase)
        except secrets.WrongPassphrase as error:
            self.app.notify(str(error), severity="error")
            return None
        self.passphrase = passphrase
        return passphrase

    async def ask_new_passphrase(self) -> str | None:
        first = await self.app.push_screen_wait(PromptScreen("New passphrase", password=True))
        second = await self.app.push_screen_wait(PromptScreen("Repeat the new passphrase", password=True))
        if not first or first != second:
            self.app.notify("Passphrases are empty or do not match", severity="error")
            return None
        return first

    @work
    async def action_unlock(self) -> None:
        if passphrase := await self.ask_passphrase():
            secrets.write_local(secrets.decrypt(passphrase))
            self.app.notify("Secrets written, open a new shell to load them")
        self.reload()

    @work
    async def action_set_secret(self) -> None:
        name = await self.app.push_screen_wait(PromptScreen("Secret name", "MY_API_KEY"))
        value = await self.app.push_screen_wait(PromptScreen(f"Value of {name}", password=True)) if name else None
        passphrase = await self.ask_passphrase() if value else None
        if name and value and passphrase:
            secrets.save({**secrets.decrypt(passphrase), name: value}, passphrase)
        self.reload()

    @work
    async def action_remove_secret(self) -> None:
        name = self.highlighted_key("#secrets-table")
        confirmed = await self.app.push_screen_wait(ConfirmScreen(f"Remove {name}?")) if name else False
        passphrase = await self.ask_passphrase() if confirmed else None
        if name and passphrase:
            values = secrets.decrypt(passphrase)
            values.pop(name, None)
            secrets.save(values, passphrase)
        self.reload()

    @work
    async def action_migrate(self) -> None:
        if secrets.has_vault():
            self.app.notify("secrets.age already exists, use a to add secrets", severity="warning")
            return
        values = secrets.from_environment(secrets.names())
        missing = sorted(set(secrets.names()) - set(values))
        if passphrase := await self.ask_new_passphrase():
            secrets.save(values, passphrase)
            self.passphrase = passphrase
            self.app.notify(
                f"Encrypted {len(values)} secrets" + (f", not in this shell: {', '.join(missing)}" if missing else "")
            )
        self.reload()

    @work
    async def action_change_passphrase(self) -> None:
        current = await self.ask_passphrase()
        new = await self.ask_new_passphrase() if current else None
        if current and new:
            secrets.save(secrets.decrypt(current), new)
            self.passphrase = new
            self.app.notify("Passphrase changed")
        self.reload()
