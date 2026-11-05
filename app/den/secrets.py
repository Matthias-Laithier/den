import hashlib
import json
import os
import re
import shlex
from pathlib import Path

from pyrage import passphrase as age  # ty: ignore[unresolved-import]

from den.machine.files import write_atomically
from den.machine.paths import config_dir, secrets_dir

EXPORT = re.compile(r"^export (\w+)=")
PRIVATE_FILE_MODE = 0o600


class WrongPassphrase(Exception):
    pass


def local_file() -> Path:
    return config_dir() / "secrets.zsh"


def _fingerprint_file() -> Path:
    return config_dir() / "secrets.sha256"


def _encrypted_file() -> Path:
    return secrets_dir() / "secrets.age"


def _names_file() -> Path:
    return secrets_dir() / "names.txt"


def names() -> list[str]:
    path = _names_file()
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def local_names() -> set[str]:
    if not local_file().exists():
        return set()
    return {match.group(1) for line in local_file().read_text().splitlines() if (match := EXPORT.match(line))}


def has_vault() -> bool:
    return _encrypted_file().exists()


def _fingerprint() -> str:
    path = _encrypted_file()
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def is_outdated() -> bool:
    if not has_vault():
        return False
    fingerprint = _fingerprint_file()
    return not local_file().exists() or not fingerprint.exists() or fingerprint.read_text() != _fingerprint()


def decrypt(passphrase: str) -> dict[str, str]:
    if not has_vault():
        return {}
    try:
        return json.loads(age.decrypt(_encrypted_file().read_bytes(), passphrase))
    except Exception as error:
        raise WrongPassphrase("Wrong passphrase") from error


def write_local(values: dict[str, str]) -> None:
    lines = [f"export {name}={shlex.quote(value)}" for name, value in sorted(values.items())]
    write_atomically(local_file(), "\n".join(lines) + "\n", PRIVATE_FILE_MODE)
    write_atomically(_fingerprint_file(), _fingerprint(), PRIVATE_FILE_MODE)


def save(values: dict[str, str], passphrase: str) -> None:
    secrets_dir().mkdir(parents=True, exist_ok=True)
    write_atomically(_encrypted_file(), age.encrypt(json.dumps(values, sort_keys=True).encode(), passphrase))
    write_atomically(_names_file(), "".join(f"{name}\n" for name in sorted(values)))
    write_local(values)


def from_environment(wanted: list[str]) -> dict[str, str]:
    return {name: os.environ[name] for name in wanted if os.environ.get(name)}
