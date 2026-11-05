import platform
from dataclasses import dataclass
from pathlib import Path

OS_RELEASE = Path("/etc/os-release")
ARM_MACHINES = {"arm64", "aarch64"}
SUPPORTED_LINUX_FAMILIES = ("arch", "debian")


@dataclass(frozen=True)
class System:
    os: str
    name: str
    arch: str


def _os_release() -> dict[str, str]:
    if not OS_RELEASE.exists():
        return {}
    fields = {}
    for line in OS_RELEASE.read_text().splitlines():
        key, _, value = line.partition("=")
        fields[key] = value.strip('"')
    return fields


def _arch() -> str:
    machine = platform.machine().lower()
    return "arm64" if machine in ARM_MACHINES else machine


def _linux_family(release: dict[str, str]) -> str:
    family = [release.get("ID", ""), *release.get("ID_LIKE", "").split()]
    return next((name for name in SUPPORTED_LINUX_FAMILIES if name in family), "unknown")


def detect() -> System:
    if platform.system() == "Darwin":
        return System("macos", f"macOS {platform.mac_ver()[0]}", _arch())
    release = _os_release()
    return System(_linux_family(release), release.get("PRETTY_NAME", platform.system()), _arch())
