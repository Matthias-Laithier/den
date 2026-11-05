import tomllib

from den.machine.paths import home_packages, manifest_dir
from den.machine.system import System
from den.manifest.models import Agent, Manifest, Package, SettingsFile, Task
from den.services.shell import succeeds

METHODS_BY_OS = {
    "macos": ["cask", "brew", "uv_tool", "npm", "script"],
    "arch": ["pacman", "aur", "uv_tool", "npm", "script"],
    "debian": ["apt", "uv_tool", "npm", "script"],
}


class InvalidManifest(Exception):
    pass


def _read(file_name: str) -> dict[str, dict]:
    path = manifest_dir() / file_name
    if not path.exists():
        return {}
    try:
        document = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        raise InvalidManifest(f"{file_name}: {error}") from error
    invalid = [name for name, entry in document.items() if not isinstance(entry, dict)]
    if invalid:
        raise InvalidManifest(f"{file_name}: {', '.join(invalid)} must be tables")
    return document


def _for_os(value, os: str):
    return value.get(os) if isinstance(value, dict) else value


def _applies(entry: dict, system: System, profiles: list[str]) -> bool:
    if "os" in entry and system.os not in entry["os"]:
        return False
    if entry.get("profiles") and not set(entry["profiles"]) & set(profiles):
        return False
    return "when" not in entry or succeeds(entry["when"])


def _package(name: str, entry: dict, os: str) -> Package | None:
    for method in METHODS_BY_OS.get(os, []):
        value = _for_os(entry.get(method), os)
        if value is None:
            continue
        return Package(
            name=name,
            group=entry.get("group", "other"),
            method=method,
            targets=(value,) if isinstance(value, str) else tuple(value),
            check=_for_os(entry.get("check"), os),
            post_install=_for_os(entry.get("post_install"), os),
        )
    return None


def _task(name: str, entry: dict, os: str) -> Task:
    return Task(
        name=name,
        description=entry.get("description", name),
        check=_for_os(entry.get("check"), os),
        run=_for_os(entry.get("run"), os),
        manual=_for_os(entry.get("manual"), os),
    )


def _agent(name: str, entry: dict, settings: tuple[SettingsFile, ...]) -> Agent:
    if not isinstance(entry.get("home"), str) or not isinstance(entry.get("skills"), (str, type(None))):
        raise InvalidManifest(f"agents.toml: {name} needs a home path and an optional skills path")
    return Agent(
        name,
        entry["home"],
        entry.get("skills"),
        entry.get("package"),
        entry.get("version"),
        entry.get("instructions"),
        settings,
    )


def _settings_files(name: str, files: dict) -> tuple[SettingsFile, ...]:
    invalid = [file for file, values in files.items() if not isinstance(values, dict)]
    if invalid:
        raise InvalidManifest(f"agent-settings.toml: {name}.{', '.join(invalid)} must be tables")
    return tuple(SettingsFile(file, values) for file, values in files.items())


def _agents(system: System, profiles: list[str]) -> list[Agent]:
    entries = _read("agents.toml")
    settings = _read("agent-settings.toml")
    unknown = sorted(settings.keys() - entries.keys())
    if unknown:
        raise InvalidManifest(f"agent-settings.toml: {', '.join(unknown)} not in agents.toml")
    return [
        _agent(name, entry, _settings_files(name, settings.get(name, {})))
        for name, entry in entries.items()
        if _applies(entry, system, profiles)
    ]


def _applicable(file_name: str, system: System, profiles: list[str]) -> dict[str, dict]:
    return {name: entry for name, entry in _read(file_name).items() if _applies(entry, system, profiles)}


def _link_packages(system: System, profiles: list[str]) -> list[str]:
    root = home_packages()
    if not root.exists():
        return []
    rules = _read("links.toml")
    names = (path.name for path in root.iterdir() if path.is_dir())
    return sorted(name for name in names if _applies(rules.get(name, {}), system, profiles))


def load(system: System, profiles: list[str]) -> Manifest:
    packages = (
        _package(name, entry, system.os) for name, entry in _applicable("packages.toml", system, profiles).items()
    )
    return Manifest(
        packages=[package for package in packages if package],
        tasks=[_task(name, entry, system.os) for name, entry in _applicable("tasks.toml", system, profiles).items()],
        agents=_agents(system, profiles),
        link_packages=_link_packages(system, profiles),
    )
