import json
import re
import shlex
from pathlib import Path

from den.services.package_managers.registry import UPDATE_CHECK_TIMEOUT_SECONDS, lines, package_manager
from den.services.shell import is_available, output

UV_OUTDATED = re.compile(r"^(\S+) v\S+ \[latest: (\S+)\]")
NPM_OUTDATED_FOUND = (0, 1)


@package_manager("uv_tool")
class UvTool:
    def installed(self) -> set[str]:
        return {row.split()[0].lower() for row in lines("uv", "tool", "list") if not row.startswith("-")}

    def outdated(self) -> dict[str, str]:
        matches = (UV_OUTDATED.match(row) for row in lines("uv", "tool", "list", "--outdated"))
        return {match.group(1).lower(): match.group(2) for match in matches if match}

    def install_commands(self, targets: list[str]) -> list[str]:
        return [f"uv tool install {shlex.quote(target)}" for target in targets]

    def upgrade_commands(self, targets: list[str]) -> list[str]:
        return [f"uv tool upgrade {shlex.join(targets)}"]


@package_manager("npm")
class NpmGlobal:
    def installed(self) -> set[str]:
        if not is_available("npm"):
            return set()
        root = Path(output("npm", "root", "-g").strip())
        scoped = {f"{scope.name}/{package.name}" for scope in root.glob("@*") for package in scope.iterdir()}
        return {path.name.lower() for path in root.iterdir() if not path.name.startswith("@")} | scoped

    def outdated(self) -> dict[str, str]:
        if not is_available("npm"):
            return {}
        report = output(
            "npm",
            "outdated",
            "-g",
            "--json",
            accepted_exit_codes=NPM_OUTDATED_FOUND,
            timeout=UPDATE_CHECK_TIMEOUT_SECONDS,
        )
        return {name.lower(): entry["latest"] for name, entry in json.loads(report or "{}").items()}

    def install_commands(self, targets: list[str]) -> list[str]:
        return [f"npm install -g {shlex.join(targets)}"]

    def upgrade_commands(self, targets: list[str]) -> list[str]:
        return [f"npm install -g {shlex.join(f'{target}@latest' for target in targets)}"]


@package_manager("script")
class Script:
    def installed(self) -> set[str]:
        return set()

    def outdated(self) -> dict[str, str]:
        return {}

    def install_commands(self, targets: list[str]) -> list[str]:
        return targets

    def upgrade_commands(self, targets: list[str]) -> list[str]:
        return []
