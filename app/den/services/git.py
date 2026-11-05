import subprocess
from dataclasses import dataclass
from pathlib import Path

UNTRACKED = "??"
GIT_TIMEOUT_SECONDS = 120
HOOKS_DIRECTORY = ".githooks"
STATUS_LABELS = {
    UNTRACKED: "new",
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "U": "conflict",
}


class GitError(Exception):
    pass


@dataclass(frozen=True)
class Change:
    path: str
    code: str

    @property
    def label(self) -> str:
        if self.code == UNTRACKED:
            return STATUS_LABELS[UNTRACKED]
        letters = [letter for letter in self.code if letter in STATUS_LABELS]
        return STATUS_LABELS[letters[0]] if letters else self.code.strip()


@dataclass(frozen=True)
class RepoState:
    branch: str
    upstream: str | None
    ahead: int
    behind: int
    changes: list[Change]


def _parse_status(output: str) -> list[Change]:
    entries = iter(output.split("\0"))
    changes = []
    for entry in entries:
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if code[0] in "RC":
            next(entries, None)
        changes.append(Change(path, code))
    return changes


def diff_files(left: Path, right: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--no-index", "--", str(left), str(right)],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise GitError(f"Comparing {left} and {right} timed out") from error
    return result.stdout


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _execute(self, *args: str) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                ["git", "-C", str(self.root), *args],
                capture_output=True,
                text=True,
                timeout=GIT_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise GitError(f"git {' '.join(args)} timed out after {GIT_TIMEOUT_SECONDS}s") from error

    def _run(self, *args: str, check: bool = True) -> str:
        result = self._execute(*args)
        if check and result.returncode != 0:
            raise GitError(result.stderr.strip() or result.stdout.strip())
        return result.stdout

    def _succeeds(self, *args: str) -> bool:
        return self._execute(*args).returncode == 0

    def has_head(self) -> bool:
        return self._succeeds("rev-parse", "--verify", "--quiet", "HEAD")

    def upstream(self) -> str | None:
        if not self._succeeds("rev-parse", "--abbrev-ref", "@{u}"):
            return None
        return self._run("rev-parse", "--abbrev-ref", "@{u}").strip()

    def state(self) -> RepoState:
        upstream = self.upstream()
        ahead, behind = 0, 0
        if upstream and self.has_head():
            ahead, behind = map(int, self._run("rev-list", "--left-right", "--count", "HEAD...@{u}").split())
        branch = self._run("branch", "--show-current").strip() or "detached"
        changes = _parse_status(self._run("status", "--porcelain=v1", "-z", "--untracked-files=all"))
        return RepoState(branch, upstream, ahead, behind, changes)

    def diff(self, change: Change) -> str:
        if change.code == UNTRACKED or not self.has_head():
            return diff_files(Path("/dev/null"), self.root / change.path)
        return self._run("diff", "HEAD", "--", change.path)

    def diff_path(self, path: Path) -> str:
        if not self.has_head():
            return ""
        return self._run("diff", "HEAD", "--", str(path.relative_to(self.root)))

    def ensure_hooks(self) -> None:
        if (self.root / HOOKS_DIRECTORY).is_dir():
            self._run("config", "core.hooksPath", HOOKS_DIRECTORY)

    def commit(self, message: str) -> None:
        self._run("add", "--all")
        self._run("commit", "--message", message)

    def pull(self) -> str:
        if self.upstream() is None:
            raise GitError("No upstream branch to pull from")
        return self._run("pull", "--ff-only").strip()

    def push(self) -> str:
        if self.upstream() is not None:
            return self._run("push").strip()
        if not self._succeeds("remote", "get-url", "origin"):
            raise GitError("No remote named origin")
        branch = self._run("branch", "--show-current").strip()
        return self._run("push", "--set-upstream", "origin", branch).strip()
