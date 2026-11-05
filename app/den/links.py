import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from den import backups
from den.machine.paths import home, home_packages

IGNORED = {".DS_Store"}


@dataclass(frozen=True)
class Link:
    package: str
    source: Path
    target: Path
    state: str

    @property
    def relative(self) -> str:
        return str(self.target.relative_to(home()))


def _mirrors_source(target: Path, relative: Path) -> bool:
    return str(target.resolve()).endswith(str(relative))


def _is_container(source: Path, target: Path, relative: Path, shared: frozenset[Path]) -> bool:
    if not source.is_dir():
        return False
    if target.is_symlink():
        return target.is_dir() and not _mirrors_source(target, relative)
    if target.exists():
        return target.is_dir()
    return relative in shared


def _state(source: Path, target: Path) -> str:
    if target.is_symlink():
        return "linked" if target.resolve() == source.resolve() else "stale"
    return "conflict" if target.exists() else "missing"


def _visit(package: str, source: Path, relative: Path, shared: frozenset[Path], links: list[Link]) -> None:
    target = home() / relative
    if not _is_container(source, target, relative, shared):
        links.append(Link(package, source, target, _state(source, target)))
        return
    for child in sorted(source.iterdir()):
        if child.name not in IGNORED:
            _visit(package, child, relative / child.name, shared, links)


def _directories(package: str) -> set[Path]:
    root = home_packages() / package
    return {path.relative_to(root) for path in root.rglob("*") if path.is_dir()}


def shared_directories(packages: list[str]) -> frozenset[Path]:
    counts = Counter(directory for package in packages for directory in _directories(package))
    return frozenset(directory for directory, count in counts.items() if count > 1)


def plan(package: str, shared: frozenset[Path] = frozenset()) -> list[Link]:
    links: list[Link] = []
    _visit(package, home_packages() / package, Path(), shared | {Path()}, links)
    return links


def plan_all(packages: list[str]) -> list[Link]:
    shared = shared_directories(packages)
    return [link for package in packages for link in plan(package, shared)]


def _symlink(link: Link) -> None:
    link.target.parent.mkdir(parents=True, exist_ok=True)
    link.target.symlink_to(link.source)


def apply(link: Link, backup_root: Path | None = None) -> None:
    if link.state == "linked":
        return
    if link.state == "stale":
        link.target.unlink()
    elif link.state == "conflict":
        destination = (backup_root or backups.new_folder()) / link.relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(link.target, destination)
    _symlink(link)


def adopt(link: Link) -> None:
    if link.state != "conflict":
        return
    if link.source.is_dir():
        shutil.rmtree(link.source)
        shutil.copytree(link.target, link.source, symlinks=True)
        shutil.rmtree(link.target)
    else:
        shutil.copy2(link.target, link.source)
        link.target.unlink()
    _symlink(link)


def apply_all(links: list[Link]) -> Path | None:
    root = backups.new_folder()
    for link in links:
        apply(link, root)
    return root if root.exists() else None
