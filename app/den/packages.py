from collections import defaultdict

from den.manifest.models import Package
from den.services import package_managers
from den.services.shell import succeeds


def _short_name(target: str) -> str:
    return target.lower() if target.startswith("@") else target.rsplit("/", 1)[-1].lower()


def _is_installed(package: Package, installed_by_method: dict[str, set[str]]) -> bool:
    if package.check:
        return succeeds(package.check)
    if package.method == "script":
        return succeeds(f"command -v {package.name}")
    installed = installed_by_method[package.method]
    return all(_short_name(target) in installed for target in package.targets)


def statuses(packages: list[Package]) -> dict[str, bool]:
    methods = {package.method for package in packages if not package.check}
    installed_by_method = {method: package_managers.get(method).installed() for method in methods}
    return {package.name: _is_installed(package, installed_by_method) for package in packages}


def _outdated_targets(package: Package, outdated: dict[str, str]) -> dict[str, str]:
    return {target: outdated[_short_name(target)] for target in package.targets if _short_name(target) in outdated}


def updates(packages: list[Package]) -> dict[str, dict[str, str]]:
    outdated_by_method = {method: package_managers.get(method).outdated() for method in {p.method for p in packages}}
    found = {package.name: _outdated_targets(package, outdated_by_method[package.method]) for package in packages}
    return {name: targets for name, targets in found.items() if targets}


def _targets_by_method(chosen: list[tuple[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for method, target in chosen:
        grouped[method].append(target)
    return grouped


def install_steps(packages: list[Package]) -> list[str]:
    grouped = _targets_by_method([(package.method, target) for package in packages for target in package.targets])
    steps = [
        step for method, targets in grouped.items() for step in package_managers.get(method).install_commands(targets)
    ]
    return steps + [package.post_install for package in packages if package.post_install]


def update_steps(packages: list[Package], available: dict[str, dict[str, str]]) -> list[str]:
    chosen = [(package.method, target) for package in packages for target in available.get(package.name, {})]
    grouped = _targets_by_method(chosen)
    steps = [
        step for method, targets in grouped.items() for step in package_managers.get(method).upgrade_commands(targets)
    ]
    return list(dict.fromkeys(steps))
