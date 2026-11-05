from typing import Protocol

from den.services.shell import is_available, output

_MANAGERS: dict[str, "PackageManager"] = {}
UPDATE_CHECK_TIMEOUT_SECONDS = 300


class PackageManager(Protocol):
    def installed(self) -> set[str]: ...

    def outdated(self) -> dict[str, str]: ...

    def install_commands(self, targets: list[str]) -> list[str]: ...

    def upgrade_commands(self, targets: list[str]) -> list[str]: ...


class UnknownPackageManager(Exception):
    pass


def package_manager(method: str):
    def register(manager_class):
        if method in _MANAGERS:
            raise ValueError(f"duplicate package manager: {method}")
        _MANAGERS[method] = manager_class()
        return manager_class

    return register


def get(method: str) -> PackageManager:
    if method not in _MANAGERS:
        raise UnknownPackageManager(method)
    return _MANAGERS[method]


def lines(*args: str, accepted_exit_codes: tuple[int, ...] = (0,)) -> list[str]:
    if not is_available(args[0]):
        return []
    text = output(*args, accepted_exit_codes=accepted_exit_codes, timeout=UPDATE_CHECK_TIMEOUT_SECONDS)
    return [line.strip() for line in text.splitlines() if line.strip()]
