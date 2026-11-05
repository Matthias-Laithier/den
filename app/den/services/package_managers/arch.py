import shlex

from den.services.package_managers.registry import lines, package_manager
from den.services.shell import is_available

AUR_HELPER = "$(command -v yay || command -v paru || { echo 'Install yay or paru first' >&2; exit 1; })"
NOTHING_TO_UPGRADE = (0, 1)
AUR_HELPERS = ("yay", "paru")


def _installed() -> set[str]:
    groups = {line.split()[0] for line in lines("pacman", "-Qg")}
    return {line.lower() for line in lines("pacman", "-Qq")} | groups


def _upgradable(*command: str) -> dict[str, str]:
    return {
        line.split()[0].lower(): line.split()[-1] for line in lines(*command, accepted_exit_codes=NOTHING_TO_UPGRADE)
    }


@package_manager("pacman")
class Pacman:
    def installed(self) -> set[str]:
        return _installed()

    def outdated(self) -> dict[str, str]:
        return _upgradable("pacman", "-Qun")

    def install_commands(self, targets: list[str]) -> list[str]:
        return [f"sudo pacman -S --needed --noconfirm {shlex.join(targets)}"]

    def upgrade_commands(self, targets: list[str]) -> list[str]:
        return ["sudo pacman -Syu --noconfirm"]


@package_manager("aur")
class ArchUserRepository:
    def installed(self) -> set[str]:
        return _installed()

    def outdated(self) -> dict[str, str]:
        helper = next((name for name in AUR_HELPERS if is_available(name)), None)
        return _upgradable(helper, "-Qua") if helper else {}

    def install_commands(self, targets: list[str]) -> list[str]:
        return [f"{AUR_HELPER} -S --needed --noconfirm {shlex.join(targets)}"]

    def upgrade_commands(self, targets: list[str]) -> list[str]:
        return [f"{AUR_HELPER} -S --noconfirm {shlex.join(targets)}"]
