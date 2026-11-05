from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from den import skills
from den.screens.document_view import DocumentView

FOLDER_ICON = "▸"
FILE_ICON = "·"
GIT_STYLES = {"new": "green", "added": "green", "modified": "yellow", "deleted": "red"}


def _file_label(relative: Path, is_folder: bool) -> Text:
    indent = "  " * (len(relative.parts) - 1)
    if is_folder:
        label = Text.assemble(indent, (f"{FOLDER_ICON} {relative.name}/", "bold cyan"))
    else:
        label = Text.assemble(indent, (f"{FILE_ICON} ", "dim"), relative.name)
    label.no_wrap = True
    label.overflow = "ellipsis"
    return label


def _header(skill: skills.Skill, git_label: str, file_count: int) -> Text:
    status = (f"  ● {git_label}", GIT_STYLES.get(git_label, "")) if git_label else ""
    files = "1 file" if file_count == 1 else f"{file_count} files"
    return Text.assemble((skill.name, "bold"), status, (f"  ·  {files}\n", "dim"), (skill.description, "italic dim"))


class SkillPreview(Vertical):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.skill: skills.Skill | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="skill-header")
        with Horizontal(id="skill-body"):
            yield OptionList(id="skill-files")
            yield DocumentView(id="skill-document")

    @property
    def current(self) -> Path | None:
        return self.query_one(DocumentView).path

    def show(self, skill: skills.Skill, git_label: str) -> None:
        self.skill = skill
        entries = skills.files(skill)
        file_list = self.query_one(OptionList)
        file_list.clear_options()
        for relative in entries:
            is_folder = (skill.path / relative).is_dir()
            file_list.add_option(Option(_file_label(relative, is_folder), id=str(relative), disabled=is_folder))
        file_count = sum(1 for entry in entries if not (skill.path / entry).is_dir())
        file_list.display = file_count > 1
        self.query_one("#skill-header", Static).update(_header(skill, git_label, file_count))
        self.query_one(DocumentView).show_file(skill.path / skills.SKILL_FILE)

    def show_diff(self, diff: str) -> None:
        self.query_one(DocumentView).show_diff(diff)

    @on(OptionList.OptionHighlighted)
    @on(OptionList.OptionSelected)
    def preview_file(self, event: OptionList.OptionHighlighted | OptionList.OptionSelected) -> None:
        event.stop()
        if self.skill is not None and event.option.id:
            self.query_one(DocumentView).show_file(self.skill.path / event.option.id)
