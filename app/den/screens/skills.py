from typing import ClassVar

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Input, OptionList

from den import skills
from den.machine.paths import files_root, skills_dir
from den.screens.dialogs import ConfirmScreen, PromptScreen
from den.screens.import_skills import ImportSkillsScreen
from den.screens.pane import Pane
from den.screens.skill_preview import GIT_STYLES, SkillPreview
from den.services.git import Change


def changed_skills(changes: list[Change]) -> dict[str, str]:
    prefix = f"{skills_dir().relative_to(files_root())}/"
    labels: dict[str, str] = {}
    for change in changes:
        if change.path.startswith(prefix):
            labels.setdefault(change.path[len(prefix) :].split("/", 1)[0], change.label)
    return labels


class SkillsPane(Pane):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "add", "Add from folder, file or GitHub"),
        Binding("x", "remove", "Remove"),
        Binding("e", "edit_previewed", "Edit file"),
        Binding("f", "browse_files", "Files"),
        Binding("d", "show_diff", "Diff"),
        Binding("slash", "filter", "Filter"),
    ]

    def __init__(self, context, **kwargs) -> None:
        super().__init__(context, **kwargs)
        self.skills: dict[str, skills.Skill] = {}
        self.labels: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(classes="split"):
            with Vertical(id="skills-sidebar"):
                yield Input(placeholder="Filter skills", id="skills-filter")
                yield DataTable(id="skills-table", cursor_type="row", show_header=False)
            yield SkillPreview(id="skill-preview")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_column("Skill")
        self.reload()

    @work(thread=True, exit_on_error=False, exclusive=True)
    def reload(self) -> None:
        installed = skills.installed()
        labels = changed_skills(self.context.repo.state().changes)
        self.app.call_from_thread(self.show, installed, labels)

    def show(self, installed: list[skills.Skill], labels: dict[str, str]) -> None:
        if self.is_already_shown((installed, labels)):
            return
        self.skills, self.labels = {skill.name: skill for skill in installed}, labels
        self.show_rows()

    def show_rows(self) -> None:
        query = self.query_one("#skills-filter", Input).value.strip().lower()
        visible = [skill for skill in self.skills.values() if query in skill.name.lower()]
        table = self.query_one(DataTable)
        cursor = table.cursor_row
        table.clear()
        for skill in visible:
            label = self.labels.get(skill.name, "")
            marker = ("● ", GIT_STYLES.get(label, "")) if label else "  "
            table.add_row(Text.assemble(marker, skill.name), key=skill.name)
        table.move_cursor(row=cursor)

    def highlighted_skill(self) -> skills.Skill | None:
        return self.skills.get(self.highlighted_key("#skills-table") or "")

    @on(DataTable.RowHighlighted)
    def show_skill(self) -> None:
        skill = self.highlighted_skill()
        if skill is not None:
            self.query_one(SkillPreview).show(skill, self.labels.get(skill.name, ""))

    def action_browse_files(self) -> None:
        self.query_one(OptionList).focus()

    @work(thread=True, exit_on_error=False, exclusive=True, group="diff")
    def action_show_diff(self) -> None:
        skill = self.highlighted_skill()
        if skill is not None:
            diff = self.context.repo.diff_path(skill.path)
            self.app.call_from_thread(self.query_one(SkillPreview).show_diff, diff)

    @work
    async def action_add(self) -> None:
        source = await self.app.push_screen_wait(
            PromptScreen("Import skills", "Folder, SKILL.md path, GitHub URL or owner/repo")
        )
        if source:
            imported = await self.app.push_screen_wait(ImportSkillsScreen(source))
            self.app.notify(f"Imported {imported} skills")
        self.reload()

    @work
    async def action_remove(self) -> None:
        skill = self.highlighted_skill()
        if skill and await self.app.push_screen_wait(ConfirmScreen(f"Remove the {skill.name} skill?")):
            skills.remove(skill.name)
        self.reload()

    def action_edit_previewed(self) -> None:
        preview = self.query_one(SkillPreview)
        skill = self.highlighted_skill()
        target = preview.current or (skill.path / skills.SKILL_FILE if skill else None)
        if target is not None:
            self.edit(target)

    def action_filter(self) -> None:
        self.query_one("#skills-filter", Input).focus()

    @on(Input.Changed, "#skills-filter")
    def filter_skills(self) -> None:
        self.show_rows()

    @on(Input.Submitted, "#skills-filter")
    def leave_filter(self) -> None:
        self.query_one("#skills-table", DataTable).focus()
