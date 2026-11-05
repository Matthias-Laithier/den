import json
import shlex

from den.services.package_managers.registry import UPDATE_CHECK_TIMEOUT_SECONDS, lines, package_manager
from den.services.shell import is_available, output

REPORT_KEYS = {"formula": "formulae", "cask": "casks"}
BREW = "HOMEBREW_NO_ASK=1 brew"
TAP_TARGET_SLASHES = 2


def _outdated(kind: str) -> dict[str, str]:
    if not is_available("brew"):
        return {}
    output("brew", "update", "--quiet", timeout=UPDATE_CHECK_TIMEOUT_SECONDS)
    report = json.loads(output("brew", "outdated", f"--{kind}", "--json=v2", timeout=UPDATE_CHECK_TIMEOUT_SECONDS))
    return {entry["name"].lower(): entry["current_version"] for entry in report[REPORT_KEYS[kind]]}


def _trust_commands(kind: str, targets: list[str]) -> list[str]:
    from_taps = [target for target in targets if target.count("/") == TAP_TARGET_SLASHES]
    return [f"{BREW} trust --{kind} {shlex.join(from_taps)}"] if from_taps else []


@package_manager("brew")
class Homebrew:
    def installed(self) -> set[str]:
        return {line.lower() for line in lines("brew", "list", "--formula", "-1")}

    def outdated(self) -> dict[str, str]:
        return _outdated("formula")

    def install_commands(self, targets: list[str]) -> list[str]:
        return _trust_commands("formula", targets) + [f"{BREW} install {shlex.join(targets)}"]

    def upgrade_commands(self, targets: list[str]) -> list[str]:
        return [f"{BREW} upgrade --formula {shlex.join(targets)}"]


@package_manager("cask")
class HomebrewCask:
    def installed(self) -> set[str]:
        return {line.lower() for line in lines("brew", "list", "--cask", "-1")}

    def outdated(self) -> dict[str, str]:
        return _outdated("cask")

    def install_commands(self, targets: list[str]) -> list[str]:
        return _trust_commands("cask", targets) + [f"{BREW} install --cask {shlex.join(targets)}"]

    def upgrade_commands(self, targets: list[str]) -> list[str]:
        return [f"{BREW} upgrade --cask {shlex.join(targets)}"]
