import shlex

from den.services.package_managers.registry import lines, package_manager


@package_manager("apt")
class Apt:
    def installed(self) -> set[str]:
        rows = lines("dpkg-query", "-W", "-f=${Package} ${Status}\n")
        return {row.split()[0].lower() for row in rows if row.endswith("install ok installed")}

    def outdated(self) -> dict[str, str]:
        rows = [row for row in lines("apt", "list", "--upgradable") if "/" in row]
        return {row.split("/", 1)[0].lower(): row.split()[1] for row in rows}

    def install_commands(self, targets: list[str]) -> list[str]:
        return [f"sudo apt-get update && sudo apt-get install -y {shlex.join(targets)}"]

    def upgrade_commands(self, targets: list[str]) -> list[str]:
        return [f"sudo apt-get update && sudo apt-get install -y --only-upgrade {shlex.join(targets)}"]
