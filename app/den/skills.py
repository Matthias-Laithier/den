import filecmp
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml

from den.machine.paths import skills_dir
from den.services.git import diff_files

SKIPPED_DIRS = {".git", "node_modules", ".venv"}
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)
SKILL_FILE = "SKILL.md"
IGNORED_FILES = {".DS_Store"}


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    path: Path


@dataclass(frozen=True)
class Candidate:
    name: str
    description: str
    source: Path
    status: str

    @property
    def loose(self) -> bool:
        return self.source.is_file()


def frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(errors="replace")
    match = FRONTMATTER.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _describe(skill_md: Path, fallback: str) -> tuple[str, str]:
    data = frontmatter(skill_md)
    name = str(data.get("name") or fallback)
    description = " ".join(str(data.get("description", "")).split())
    return name, description


def installed() -> list[Skill]:
    root = skills_dir()
    if not root.exists():
        return []
    skills = []
    for skill_md in sorted(root.glob("*/SKILL.md")):
        _, description = _describe(skill_md, skill_md.parent.name)
        skills.append(Skill(skill_md.parent.name, description, skill_md.parent))
    return skills


def markdown_body(path: Path) -> str:
    return FRONTMATTER.sub("", path.read_text(errors="replace"), count=1)


def _walk(folder: Path, root: Path) -> list[Path]:
    children = sorted(path for path in folder.iterdir() if path.name not in IGNORED_FILES)
    ordered = sorted(children, key=lambda path: (path.name != SKILL_FILE, path.is_dir(), path.name.lower()))
    found = []
    for child in ordered:
        found.append(child.relative_to(root))
        if child.is_dir():
            found.extend(_walk(child, root))
    return found


def files(skill: Skill) -> list[Path]:
    return _walk(skill.path, skill.path)


def _same_tree(left: Path, right: Path) -> bool:
    comparison = filecmp.dircmp(left, right, ignore=[".DS_Store"])
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(left, right, comparison.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(_same_tree(left / name, right / name) for name in comparison.common_dirs)


def _status(name: str, source: Path) -> str:
    existing = skills_dir() / name
    if not existing.exists():
        return "new"
    if source.is_file():
        same = (existing / "SKILL.md").read_bytes() == source.read_bytes() and len(list(existing.iterdir())) == 1
    else:
        same = _same_tree(existing, source)
    return "identical" if same else "conflict"


def _skill_files(source: Path) -> list[Path]:
    found = []
    for path in sorted(source.rglob("SKILL.md")):
        if not SKIPPED_DIRS & set(path.relative_to(source).parts):
            found.append(path)
    return found


def discover(source: Path) -> list[Candidate]:
    if source.is_file():
        name, description = _describe(source, source.parent.name)
        return [Candidate(name, description, source, _status(name, source))]
    candidates = []
    for skill_md in _skill_files(source):
        declared, description = _describe(skill_md, skill_md.parent.name)
        name = declared if skill_md.parent == source else skill_md.parent.name
        candidates.append(Candidate(name, description, skill_md.parent, _status(name, skill_md.parent)))
    return candidates


def _copy_into(candidate: Candidate, staging: Path) -> None:
    if candidate.loose:
        staging.mkdir(parents=True)
        shutil.copy2(candidate.source, staging / "SKILL.md")
    else:
        shutil.copytree(candidate.source, staging, ignore=shutil.ignore_patterns(".git", ".DS_Store"))


def install(candidate: Candidate, name: str | None = None) -> Path:
    root = skills_dir()
    destination = root / (name or candidate.name)
    staging = root / f".{destination.name}.importing"
    replaced = root / f".{destination.name}.replaced"
    for leftover in (staging, replaced):
        shutil.rmtree(leftover, ignore_errors=True)
    _copy_into(candidate, staging)
    if destination.exists():
        destination.rename(replaced)
    staging.rename(destination)
    shutil.rmtree(replaced, ignore_errors=True)
    return destination


def diff(candidate: Candidate) -> str:
    existing = skills_dir() / candidate.name
    target = existing / "SKILL.md" if candidate.loose else existing
    return diff_files(target, candidate.source) or "No differences"


def remove(name: str) -> None:
    shutil.rmtree(skills_dir() / name)
