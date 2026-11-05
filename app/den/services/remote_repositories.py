import re
import subprocess
import tempfile
from pathlib import Path

GITHUB_TREE = re.compile(r"^(?:https?://)?github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/tree/([^/]+)/(.+))?/?$")
GITHUB_SHORTHAND = re.compile(r"^([\w.-]+)/([\w.-]+)$")
CLONE_TIMEOUT_SECONDS = 300


class CloneFailed(Exception):
    pass


def _normalize(url: str) -> tuple[str, str | None, str | None]:
    if match := GITHUB_TREE.match(url):
        owner, repo, branch, subpath = match.groups()
        return f"https://github.com/{owner}/{repo}.git", branch, subpath
    if match := GITHUB_SHORTHAND.match(url):
        return f"https://github.com/{match.group(1)}/{match.group(2)}.git", None, None
    return url, None, None


def shallow_clone(url: str) -> tuple[tempfile.TemporaryDirectory, Path]:
    clone_url, branch, subpath = _normalize(url.strip())
    workspace = tempfile.TemporaryDirectory(prefix="den-skills-")
    command = ["git", "clone", "--depth", "1", "--quiet", *(["--branch", branch] if branch else [])]
    try:
        result = subprocess.run(
            [*command, clone_url, workspace.name],
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        workspace.cleanup()
        raise CloneFailed(f"Cloning {clone_url} took more than {CLONE_TIMEOUT_SECONDS}s") from error
    if result.returncode != 0:
        workspace.cleanup()
        raise CloneFailed(result.stderr.strip() or f"Could not clone {clone_url}")
    root = Path(workspace.name)
    return workspace, root / subpath if subpath else root
